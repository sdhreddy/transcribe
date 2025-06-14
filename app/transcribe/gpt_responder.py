import datetime
import time
from enum import Enum
import threading
# import pprint
import openai
import re
import queue
from . import prompts
from . import conversation
from . import constants
from .streaming_tts import create_tts, TTSConfig
from .audio_player_streaming import StreamingAudioPlayer
from .db import (
    AppDB as appdb,
    llm_responses as llmrdb,
    summaries as s)
from tsutils import app_logging as al
from tsutils import duration, utilities


logger = al.get_module_logger(al.GPT_RESPONDER_LOGGER)


class InferenceEnum(Enum):
    """Supported Chat Inference Providers
    """
    OPENAI = 1
    TOGETHER = 2


class GPTResponder:
    """Handles all interactions with openAI LLM / ChatGPT
    """
    # By default we do not ping LLM to get data
    enabled: bool = False
    model: str = None
    llm_client = None

    def __init__(self,
                 config: dict,
                 convo: conversation.Conversation,
                 file_name: str,
                 save_to_file: bool = False,
                 openai_module=openai):
        logger.info(GPTResponder.__name__)
        print(f"[INIT DEBUG] GPTResponder.__init__ called")
        print(f"[INIT DEBUG] Config General keys: {list(config.get('General', {}).keys())}")
        # This var is used by UI to populate the response textbox
        self.response = prompts.INITIAL_RESPONSE
        self.llm_response_interval = config['General']['llm_response_interval']
        self.conversation = convo
        self.config = config
        self.save_response_to_file = save_to_file
        self.response_file = file_name
        self.openai_module = openai_module
        self.streaming_complete = threading.Event()
        
        # Streaming TTS support
        self.buffer = ""
        self.sent_q: queue.Queue[str] = queue.Queue()
        self.SENT_END = re.compile(r"[.!?]")  # sentence boundary pattern - requires space after punctuation
        
        # Initialize TTS if enabled
        tts_enabled = config.get('General', {}).get('tts_streaming_enabled', False)
        logger.info(f"[TTS Debug] TTS streaming enabled: {tts_enabled}")
        print(f"[INIT DEBUG] tts_streaming_enabled from config: {tts_enabled}")
        print(f"[INIT DEBUG] tts_provider: {config.get('General', {}).get('tts_provider')}")
        
        if tts_enabled:
            tts_config = TTSConfig(
                provider=config.get('General', {}).get('tts_provider', 'gtts'),
                voice=config.get('General', {}).get('tts_voice', 'alloy'),
                sample_rate=config.get('General', {}).get('tts_sample_rate', 24000),
                api_key=config.get('OpenAI', {}).get('api_key')
            )
            self.tts = create_tts(tts_config)
            self.player = StreamingAudioPlayer(sample_rate=tts_config.sample_rate)
            self.player.start()
            self.tts_worker_thread = threading.Thread(target=self._tts_worker, daemon=True)
            self.tts_worker_thread.start()
            self.tts_enabled = True
            logger.info(f"[TTS Debug] Streaming TTS initialized with provider: {tts_config.provider}")
            logger.info(f"[TTS Debug] Voice: {tts_config.voice}, Sample rate: {tts_config.sample_rate}")
        else:
            self.tts_enabled = False
        self.streaming_tts_active = False  # Flag to prevent old TTS interference
        # Track current request to allow cancellation
        self._current_request = None
        self._request_lock = threading.Lock()
        self._last_processed_text = ""
        self._cancel_requested = False

    def summarize(self) -> str:
        """Ping LLM to get a summary of the conversation.
        """
        logger.info(GPTResponder.summarize.__name__)

        chat_inference_provider = self.config['General']['chat_inference_provider']
        if chat_inference_provider == 'openai':
            settings_section = 'OpenAI'
        elif chat_inference_provider == 'together':
            settings_section = 'Together'

        api_key = self.config[settings_section]['api_key']
        base_url = self.config[settings_section]['base_url']
        model = self.config[settings_section]['ai_model']

        if not utilities.is_api_key_valid(api_key=api_key, base_url=base_url, model=model):
            return None

        with duration.Duration(name='OpenAI Summarize', screen=False):
            timeout: int = self.config['OpenAI']['summarize_request_timeout_seconds']
            temperature: float = self.config['OpenAI']['temperature']
            prompt_content = self.conversation.get_merged_conversation_summary()
            prompt_api_message = prompts.create_multiturn_prompt(prompt_content)
            last_convo_id = int(prompt_content[-1][2])
            # self._pretty_print_openai_request(prompt_api_message)
            summary_response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=prompt_api_message,
                    temperature=temperature,
                    timeout=timeout,
                    stream=True
                )
            collected_messages = ""
            for chunk in summary_response:
                chunk_message = chunk.choices[0].delta  # extract the message
                if chunk_message.content:
                    message_text = chunk_message.content
                    collected_messages += message_text
                    # print(f'{message_text}', end="")

            # insert in DB
            inv_id = appdb().get_invocation_id()
            summary_obj = appdb().get_object(s.TABLE_NAME)
            summary_obj.insert_summary(inv_id, last_convo_id, collected_messages)

        return collected_messages

    def _get_settings_section(self, provider: str) -> str:
        """Get the settings section based on the chat inference provider."""
        if provider == 'openai':
            return 'OpenAI'
        elif provider == 'together':
            return 'Together'
        raise ValueError(f"Unsupported chat inference provider: {provider}")

    def _get_api_settings(self, settings_section: str):
        """Retrieve API settings from the configuration."""
        api_key = self.config[settings_section]['api_key']
        base_url = self.config[settings_section]['base_url']
        model = self.config[settings_section]['ai_model']
        return api_key, base_url, model

    def _get_openai_settings(self) -> (int, float):
        """Retrieve OpenAI-specific settings from the configuration."""
        timeout = self.config['OpenAI']['response_request_timeout_seconds']
        temperature = self.config['OpenAI']['temperature']
        return timeout, temperature

    def _cancel_current_request(self):
        """Cancel any ongoing request."""
        with self._request_lock:
            if self._current_request:
                logger.info("Cancelling previous GPT request")
                print("[INFO] Cancelling previous GPT request")
                # Set flag to stop streaming
                self._cancel_requested = True

    def _get_llm_response(self, messages, temperature, timeout) -> str:
        """Send a request to the LLM and process the streaming response."""
        self.streaming_complete.clear()
        self._cancel_requested = False
        
        with duration.Duration(name='OpenAI Chat Completion', screen=False):
            with self._request_lock:
                self._current_request = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    timeout=timeout,
                    stream=True
                )

            collected_messages = ""
            try:
                for chunk in self._current_request:
                    # Check if cancellation requested
                    if self._cancel_requested:
                        logger.info("Request cancelled, stopping stream")
                        print("[INFO] Request cancelled, stopping stream")
                        break
                        
                    chunk_message = chunk.choices[0].delta  # extract the message
                    if chunk_message.content:
                        message_text = chunk_message.content
                        collected_messages += message_text
                        self._update_conversation(persona=constants.PERSONA_ASSISTANT,
                                                  response=collected_messages,
                                                  update_previous=True)
                        self._handle_streaming_token(message_text)
            finally:
                with self._request_lock:
                    self._current_request = None
                    
            self.streaming_tts_active = False  # Clear flag
            self.streaming_complete.set()
            self.flush_tts_buffer()
            
            return collected_messages if not self._cancel_requested else None

    def _insert_response_in_db(self, last_convo_id: int, response: str):
        """Insert the generated response into the database."""
        inv_id = appdb().get_invocation_id()
        llmr_obj: llmrdb.LLMResponses = appdb().get_object(llmrdb.TABLE_NAME)
        llmr_obj.insert_response(inv_id, last_convo_id, response)

    def generate_response_from_transcript_no_check(self) -> str:
        """
        Pings the LLM to get a suggested response immediately.

        This method gets a response even if the continuous suggestion option is disabled.
        It updates the conversation object with the response from the LLM.

        Returns:
            str: The generated response from the LLM.
        """
        logger.info(GPTResponder.generate_response_from_transcript_no_check.__name__)
        
        # Cancel any ongoing request first
        self._cancel_current_request()

        try:
            chat_inference_provider = self.config['General']['chat_inference_provider']
            settings_section = self._get_settings_section(chat_inference_provider)
            api_key, base_url, model = self._get_api_settings(settings_section)

            if not utilities.is_api_key_valid(api_key=api_key, base_url=base_url, model=model):
                return None

            timeout, temperature = self._get_openai_settings()
            multiturn_prompt_content = self.conversation.get_merged_conversation_response(
                length=constants.MAX_TRANSCRIPTION_PHRASES_FOR_LLM)
            last_convo_id = int(multiturn_prompt_content[-1][2])
            multiturn_prompt_api_message = prompts.create_multiturn_prompt(multiturn_prompt_content)
            collected_messages = self._get_llm_response(multiturn_prompt_api_message, temperature, timeout)
            
            # If request was cancelled, return None
            if collected_messages is None:
                logger.info("Request was cancelled, returning None")
                return None
                
            self._insert_response_in_db(last_convo_id, collected_messages)

        except Exception as e:
            logger.error(f"Error in generate_response_from_transcript_no_check: {e}")
            print(f'Error getting response from LLM: {e}')
            return None

        self._save_response_to_file(collected_messages)
        return collected_messages

    def create_client(self, api_key: str, base_url: str = None):
        """
        Create and initialize an OpenAI API compatible client.

        Args:
            api_key (str): The API key for authentication.
            base_url (str, optional): The base URL for the API. Defaults to None.

        Returns:
            None

        Raises:
            ValueError: If the API key is invalid.
            ConnectionError: If the client fails to connect.
        """
        if not api_key:
            raise ValueError("API key is required")

        try:
            if self.llm_client is not None:
                self.llm_client.close()
            self.llm_client = self.openai_module.OpenAI(api_key=api_key, base_url=base_url)
        except Exception as e:
            raise ConnectionError(f"Failed to create OpenAI client: {e}")

    def process_response(self, input_str: str) -> str:
        """
        Processes a given input string by extracting relevant data from LLM response.

        Args:
            input_str (str): The input string containing LLM response data.

        Returns:
            str: A processed string with irrelevant content removed.
        """
        if input_str is None:
            raise ValueError("input_str cannot be None")

        lines = input_str.split(sep='\n')
        response_lines = []

        for line in lines:
            # Skip any responses that contain content like
            # Speaker 1: <Some statement>
            # This is generated content added by OpenAI that can be skipped
            if 'Speaker' in line and ':' in line:
                continue
            response_lines.append(line.strip().strip('[').strip(']'))

        # Create a list and then use that to create a string for
        # performance reasons, since strings are immutable in python
        response = ''.join(response_lines)
        return response

    def generate_response_from_transcript(self) -> str:
        """
        Pings the OpenAI LLM model to get a response from the Assistant.

        Logs the method call and checks if the feature is enabled before
        proceeding with response generation.

        Returns:
            str: The response from the OpenAI LLM model.
            Returns an empty string if the feature is disabled.
        """
        logger.info("generate_response_from_transcript called")

        if not self.enabled:
            return ''

        return self.generate_response_from_transcript_no_check()

    def generate_response_for_selected_text(self, text: str):
        """Ping LLM to get a suggested response right away.
            Gets a response even if the continuous suggestion option is disabled.
            Updates the conversation object with the response from LLM.
        """
        try:
            logger.info(GPTResponder.generate_response_for_selected_text.__name__)
            chat_inference_provider = self.config['General']['chat_inference_provider']
            settings_section = self._get_settings_section(chat_inference_provider)
            api_key, base_url, model = self._get_api_settings(settings_section)

            timeout, temperature = self._get_openai_settings()

            if not utilities.is_api_key_valid(api_key=api_key, base_url=base_url, model=model):
                return None

            with duration.Duration(name='OpenAI Chat Completion Selected', screen=False):
                self.streaming_complete.clear()
                prompt = prompts.create_prompt_for_text(text=text, config=self.config)
                llm_response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=prompt,
                    temperature=temperature,
                    timeout=timeout,
                    stream=True
                )

                # Update conversation with an empty response. This response will be updated
                # by subsequent updates from the streaming response
                self._update_conversation(persona=constants.PERSONA_ASSISTANT,
                                          response="  ",
                                          update_previous=False)
                collected_messages = ""
                for chunk in llm_response:
                    chunk_message = chunk.choices[0].delta  # extract the message
                    if chunk_message.content:
                        message_text = chunk_message.content
                        collected_messages += message_text
                        # print(f"{message_text}", end="")
                        self._update_conversation(persona=constants.PERSONA_ASSISTANT,
                                                  response=collected_messages,
                                                  update_previous=True)
                        self._handle_streaming_token(message_text)
                self.streaming_tts_active = False  # Clear flag
            self.streaming_complete.set()
                self.flush_tts_buffer()
                

        except Exception as exception:
            print('Error when attempting to get a response from LLM.')
            print(exception)
            logger.error('Error when attempting to get a response from LLM.')
            logger.exception(exception)
            return prompts.INITIAL_RESPONSE

        processed_response = collected_messages

        self._save_response_to_file(processed_response)

        return processed_response

    def _save_response_to_file(self, text: str):
        if self.save_response_to_file:
            with open(file=self.response_file, mode="a", encoding='utf-8') as f:
                f.write(f'{datetime.datetime.now()} - {text}\n')

    def _update_conversation(self, response, persona, update_previous=False):
        """Update the internaal conversation state"""
        logger.info(GPTResponder._update_conversation.__name__)
        if response != '':
            self.response = response
            self.conversation.update_conversation(persona=persona,
                                                  text=response,
                                                  time_spoken=datetime.datetime.utcnow(),
                                                  update_previous=update_previous)

    def respond_to_transcriber(self, transcriber):
        """Thread method to continously update the transcript
        """
        while True:

            # Attempt to get responses only if transcript has changed
            if transcriber.transcript_changed_event.is_set():
                start_time = time.time()

                transcriber.transcript_changed_event.clear()

                # Do processing only if LLM transcription is enabled
                if self.enabled:
                    self.generate_response_from_transcript()

                end_time = time.time()  # Measure end time
                execution_time = end_time - start_time  # Calculate time to execute the function

                remaining_time = self.llm_response_interval - execution_time
                if remaining_time > 0:
                    # print(f'llm_response_interval: {self.llm_response_interval}, execution time: {execution_time}')
                    # print(f'Sleeping for a response for duration: {remaining_time}')
                    time.sleep(remaining_time)
            else:
                time.sleep(self.llm_response_interval)

    def update_response_interval(self, interval):
        """Change the interval for pinging LLM
        """
        # Very chatty log statement
        # logger.info(GPTResponder.update_response_interval.__name__)
        self.llm_response_interval = interval

    def _pretty_print_openai_request(self, message: str):
        """Format the openAI request in a nice print format"""
        print('[')
        for item in message:
            print('  {')
            print(f'    \'role\': \'{item["role"]}\'')
            print(f'    \'content\': \'{item["content"]}\'')
            print('  }')

        print(']')
    
    def _handle_streaming_token(self, token: str):
        """Handle a single token from streaming response."""
        if not hasattr(self, '_first_token_time'):
            self._first_token_time = time.time()
            logger.info(f"[TTS Debug] First GPT token received at {self._first_token_time}")
        """Handle incoming token from LLM stream for TTS processing."""
        if not self.tts_enabled:
            self.streaming_tts_active = True
            return
            
        self.buffer += token
        logger.info(f"[TTS Debug] Token received: '{token}' | Buffer length: {len(self.buffer)}")
        
        # Check for sentence boundary
        match = self.SENT_END.search(self.buffer)
        if match:
            # Extract complete sentence
            complete_sentence = self.buffer[:match.end()].strip()
            
            # Use min_sentence_chars from config (default 10 if not set)
            min_chars = self.config.get('General', {}).get('tts_min_sentence_chars', 5)
            
            if complete_sentence and len(complete_sentence) >= min_chars:
                logger.info(f"[TTS Debug] Sentence detected: '{complete_sentence}' (length: {len(complete_sentence)})")
                self.sent_q.put(complete_sentence)
                self.buffer = self.buffer[match.end():].lstrip()
                logger.info(f"[TTS Debug] Remaining buffer: '{self.buffer}'")
            else:
                logger.info(f"[TTS Debug] Sentence too short ({len(complete_sentence)} chars): '{complete_sentence}'")
        
        # Force a break if buffer gets too long without punctuation
                # Also check for commas for more natural breaks
        elif ',' in self.buffer and len(self.buffer) > 20:
            comma_pos = self.buffer.rfind(',')
            if comma_pos > 10:  # Ensure we have enough content
                partial = self.buffer[:comma_pos+1].strip()
                if partial:
                    logger.info(f"[TTS Debug] Comma break: '{partial}'")
                    self.sent_q.put(partial)
                    self.buffer = self.buffer[comma_pos+1:].strip()
                # Periodic flush check - don't let buffer grow too large
        elif len(self.buffer) > 30 and ' ' in self.buffer:
            # Find last space and break there
            last_space = self.buffer.rfind(' ')
            if last_space > 15:
                partial = self.buffer[:last_space].strip()
                if partial:
                    logger.info(f"[TTS Debug] Periodic flush at space: '{partial}'")
                    self.sent_q.put(partial)
                    self.buffer = self.buffer[last_space:].lstrip()
        elif len(self.buffer) > 42:  # Matches the OpenAI recommendation
            # Send what we have so far
            if self.buffer.strip():
                logger.info(f"[TTS Debug] Force break at {len(self.buffer)} chars: '{self.buffer.strip()}'")
                self.sent_q.put(self.buffer.strip())
                self.buffer = ""
    
    def _tts_worker(self):
        """Worker thread that converts sentences to speech and plays them."""
        logger.info("[TTS Debug] TTS worker thread started")
        logger.info(f"[TTS Debug] TTS provider: {self.tts.__class__.__name__}")
        
        while True:
            try:
                sentence = self.sent_q.get(timeout=0.5)  # Keep worker alive
                if sentence is None:  # Shutdown signal
                    break
                    
                logger.info(f"[TTS Debug] TTS processing sentence: '{sentence}' ({len(sentence)} chars)")
                start_time = time.time()
                
                # Stream TTS audio
                chunk_count = 0
                for audio_chunk in self.tts.stream(sentence):
                    if chunk_count == 0:
                        first_chunk_time = time.time() - start_time
                        logger.info(f"[TTS Debug] First audio chunk received in {first_chunk_time*1000:.0f}ms")
                    chunk_count += 1
                    self.player.enqueue(audio_chunk)
                
                total_time = time.time() - start_time
                logger.info(f"[TTS Debug] TTS completed: {chunk_count} chunks in {total_time*1000:.0f}ms")
                
                # Mark task as done for queue.join()
                self.sent_q.task_done()
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[TTS Debug] TTS worker error: {type(e).__name__}: {e}")
                # Log the full traceback for debugging
                import traceback
                logger.error(f"[TTS Debug] Full traceback:\n{traceback.format_exc()}")
                
                # Mark task as done even on error to prevent queue blocking
                try:
                    self.sent_q.task_done()
                except ValueError:
                    pass  # task_done() called too many times
                
                # Don't let the worker die - continue processing
                continue
                
        logger.info("TTS worker thread stopped")
    
    def flush_tts_buffer(self):
        """Flush any remaining text in buffer when streaming completes."""
        if self.tts_enabled and self.buffer.strip():
            logger.info(f"[TTS Debug] Flushing remaining buffer: '{self.buffer.strip()}'")
            self.sent_q.put(self.buffer.strip())
            self.buffer = ""
    
    def stop_tts(self):
        """Stop TTS playback and cleanup."""
        if self.tts_enabled:
            self.sent_q.put(None)  # Signal worker to stop
            self.player.stop()


class OpenAIResponder(GPTResponder):
    """Uses OpenAI for Chat Inference"""

    def __init__(self,
                 config: dict,
                 convo: conversation.Conversation,
                 response_file_name: str,
                 save_to_file: bool = False,
                 base_url: str = None):
        logger.info(OpenAIResponder.__name__)
        print(f"[INIT DEBUG] OpenAIResponder.__init__ called")
        print(f"[INIT DEBUG] Config has tts_streaming_enabled: {config.get('General', {}).get('tts_streaming_enabled')}")
        self.config = config
        api_key = self.config['OpenAI']['api_key']
        base_url = self.config['OpenAI']['base_url']
        self.llm_client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = self.config['OpenAI']['ai_model']
        stt = self.config['General']['stt']
        print(f'[INFO] Using {stt} for inference. Model: {self.model}')
        super().__init__(config=self.config,
                         convo=convo,
                         save_to_file=save_to_file,
                         file_name=response_file_name)


class TogetherAIResponder(GPTResponder):
    """Uses TogetherAI for Chat Inference"""

    def __init__(self,
                 config: dict,
                 convo: conversation.Conversation,
                 response_file_name: str,
                 save_to_file: bool = False):
        logger.info(TogetherAIResponder.__name__)
        self.config = config
        api_key = self.config['Together']['api_key']
        base_url = self.config['Together']['base_url']
        self.llm_client = openai.OpenAI(api_key=api_key,
                                        base_url=base_url)
        self.model = self.config['Together']['ai_model']
        print(f'[INFO] Using Together AI for inference. Model: {self.model}')
        super().__init__(config=self.config,
                         convo=convo,
                         save_to_file=save_to_file,
                         file_name=response_file_name)


class InferenceResponderFactory:
    """Factory class to get the appropriate Inference Provider / GPT Provider
    """
    def get_responder_instance(self,
                               provider: InferenceEnum,
                               config: dict,
                               convo: conversation.Conversation,
                               response_file_name: str,
                               save_to_file: bool = False,
                               ) -> GPTResponder:
        """Get the appropriate Inference Provider class instance
        Args:
          provider: InferenceEnum: The Inference provider enum
          config: dict: Used to pass all configuration parameters
          convo: Conversation: Conversation object for storing all conversation text
          save_to_file: bool: Save LLM responses to file or not
          response_file_name: str: Filename for saving LLM responses
        """
        if not isinstance(provider, InferenceEnum):
            raise TypeError('InferenceResponderFactory: provider should be an instance of InferenceEnum')

        if provider == InferenceEnum.OPENAI:
            return OpenAIResponder(config=config,
                                   convo=convo,
                                   save_to_file=save_to_file,
                                   response_file_name=response_file_name)
        elif provider == InferenceEnum.TOGETHER:
            return TogetherAIResponder(config=config,
                                       convo=convo,
                                       save_to_file=save_to_file,
                                       response_file_name=response_file_name)

        raise ValueError("Unknown Inference Provider type")


if __name__ == "__main__":
    print('GPTResponder')
