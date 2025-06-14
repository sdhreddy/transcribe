import datetime
import time
from enum import Enum
import threading
# import pprint
import openai
import prompts
import conversation
import constants
from db import (
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
    
    Voice Identification Support:
    - When voice identification is enabled and voice_based_response_control is True:
      - Unknown speakers (colleagues) always get responses, bypassing relay detection
      - Primary user speech goes through normal relay detection
    - This allows the system to respond to colleague questions while preventing
      duplicate responses when the primary user relays AI suggestions
    """

    # Global relay detection state to prevent multiple responses
    _relay_detected = False
    _relay_detection_time = None
    _relay_reset_interval = 3  # Reset after 3 seconds for faster colleague responses
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
        # This var is used by UI to populate the response textbox
        self.response = prompts.INITIAL_RESPONSE
        self.llm_response_interval = config['General']['llm_response_interval']
        self.conversation = convo
        self.config = config
        self.save_response_to_file = save_to_file
        self.response_file = file_name
        self.openai_module = openai_module
        self.streaming_complete = threading.Event()
        self.last_responded_transcript = ""  # Track last transcript we responded to
        self.last_ai_response = ""  # Track last AI response to detect when user is relaying it
        self.last_ai_response_time = None  # Track when the last response was made
        
        # Log voice identification configuration
        voice_id_config = config['General'].get('voice_identification_enabled', 'No')
        # Handle various true values (Yes, yes, True, true, 1)
        voice_id_enabled = voice_id_config in [True, 'Yes', 'yes', 'TRUE', 'true', 1, '1']
        if voice_id_enabled:
            logger.info("[VOICE_ID] Voice identification is ENABLED")
            logger.info(f"[VOICE_ID] Primary user ID: {config['General'].get('primary_user_id', 'primary_user')}")
        else:
            logger.info(f"[VOICE_ID] Voice identification is DISABLED (config value: {voice_id_config})")

    def _is_user_relaying_response(self, user_input: str) -> bool:
        """Check if user input is similar to the recent AI response (user relaying the answer)
        Enhanced to handle colleague interruption scenarios."""
        start_time = time.time()
        logger.info(f"[RELAY_CHECK_START] Checking relay for input: '{user_input[:50]}...'")
        
        if not self.last_ai_response or not user_input:
            logger.info(f"[RELAY_CHECK] No last response or input - returning False")
            return False
        
        # Check for interruption patterns that indicate a colleague is asking
        interruption_patterns = [
            "wait", "hold on", "what about", "but what if", "actually",
            "tell me more", "can you explain", "how does", "why does",
            "what happens when", "is it true that", "does that mean"
        ]
        
        user_lower = user_input.lower().strip()
        for pattern in interruption_patterns:
            if pattern in user_lower:
                logger.info(f"[RELAY_CHECK] Detected interruption pattern: '{pattern}' - treating as NEW")
                return False
        
        # Check if this might be a colleague's question (different speaking style)
        # Colleague questions often start with these patterns
        colleague_question_starters = [
            "so you're saying", "does he mean", "is he saying",
            "did the ai say", "what did it say about", "ask it",
            "can you ask", "tell him", "ask him about"
        ]
        
        for starter in colleague_question_starters:
            if user_lower.startswith(starter):
                logger.info(f"[RELAY_CHECK] Detected colleague question pattern: '{starter}' - treating as NEW")
                return False
        
        # If input is very short, it might be an interruption
        if len(user_input.split()) <= 3:
            logger.info(f"[RELAY_CHECK] Very short input, might be interruption - treating as NEW")
            return False
        
        # Reset context after 30 seconds - new questions should not be blocked
        import datetime
        current_time = datetime.datetime.utcnow()
        if (self.last_ai_response_time and 
            (current_time - self.last_ai_response_time).total_seconds() > 30):
            logger.info("Context timeout - clearing previous AI response for fresh detection")
            self.last_ai_response = ""
            return False
        
        # First try AI-based semantic similarity for better context understanding
        try:
            semantic_similarity = self._check_semantic_similarity(user_input, self.last_ai_response)
            logger.info(f"Semantic similarity score: {semantic_similarity:.2f}")
            
            # Higher threshold for relay detection to allow more colleague questions through
            if semantic_similarity > 0.75:  # Increased from 0.65
                logger.info(f"Semantic relay detected with confidence: {semantic_similarity:.2f}")
                return True
        except Exception as e:
            logger.warning(f"Semantic similarity check failed, falling back to keyword matching: {e}")
        
        # Fallback to keyword-based detection
        keyword_result = self._check_keyword_similarity(user_input, self.last_ai_response)
        elapsed = time.time() - start_time
        logger.info(f"[RELAY_CHECK_END] Result: {'RELAY' if keyword_result else 'NEW'} (keyword) - Time: {elapsed:.3f}s")
        return keyword_result
    def _check_semantic_similarity(self, user_input: str, ai_response: str) -> float:
        """Use AI to determine semantic similarity between user input and AI response"""
        prompt = f'''You are analyzing if someone is relaying/repeating information they just heard.

AI just said: "{ai_response}"

User now says: "{user_input}"

Is the user explaining/relaying the same core concepts the AI just provided? Consider:
- Paraphrasing (different words, same meaning)
- Explaining to someone else (casual language)  
- Summarizing the key points
- Using examples from the AI response

Answer with only a number 0.0-1.0:
- 0.0 = Completely new/different topic
- 0.6 = Related but adding new information
- 0.8 = Clearly relaying same concepts  
- 1.0 = Almost identical information

Number:'''
        
        try:
            # Use a simple, fast completion for similarity check
            chat_inference_provider = self.config['General']['chat_inference_provider']
            settings_section = self._get_settings_section(chat_inference_provider)
            api_key, base_url, model = self._get_api_settings(settings_section)
            
            if not utilities.is_api_key_valid(api_key=api_key, base_url=base_url, model=model):
                return 0.0
                
            # Use a faster, simpler model call for this check
            response = self.llm_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=10,
                timeout=3  # Quick timeout for fast response
            )
            
            result = response.choices[0].message.content.strip()
            # Extract number from response
            import re
            numbers = re.findall(r'0?\.\d+|1\.0|0|1', result)
            if numbers:
                return float(numbers[0])
            return 0.0
            
        except Exception as e:
            logger.warning(f"Semantic similarity API call failed: {e}")
            return 0.0
    
    def _check_keyword_similarity(self, user_input: str, ai_response: str) -> bool:
        """Enhanced keyword similarity detection that handles partial relays better"""
        import re
        
        if not user_input or not ai_response:
            return False
        
        user_lower = user_input.lower().strip()
        ai_lower = ai_response.lower().strip()
        
        # Remove punctuation for better matching
        user_normalized = re.sub(r'[^\w\s]', ' ', user_lower)
        ai_normalized = re.sub(r'[^\w\s]', ' ', ai_lower)
        
        # Clean up extra spaces
        user_normalized = re.sub(r'\s+', ' ', user_normalized).strip()
        ai_normalized = re.sub(r'\s+', ' ', ai_normalized).strip()
        
        # 1. EXACT SUBSTRING CHECK
        # Check if user input is a direct substring (handles partial reading)
        if len(user_normalized) > 8:  # Meaningful length
            if user_normalized in ai_normalized:
                logger.info(f"[RELAY_DETECT] Exact substring match found")
                return True
            
            # Check with common speech variations
            variations = {
                'cyprus': 'cypress',
                'cypress': 'cyprus',
                'qa': 'quality assurance',
                'qc': 'quality control',
                'versus': 'vs',
                'vs': 'versus',
            }
            
            # Apply variations
            user_variant = user_normalized
            for old, new in variations.items():
                user_variant = user_variant.replace(old, new)
            
            if user_variant != user_normalized and user_variant in ai_normalized:
                logger.info(f"[RELAY_DETECT] Variant substring match found")
                return True
        
        # 2. SEQUENTIAL WORD MATCHING
        user_words = user_normalized.split()
        ai_words = ai_normalized.split()
        
        if len(user_words) >= 3:  # At least 3 words
            # Track sequential matches
            matched_sequences = []
            
            # Find all positions where first user word appears in AI
            first_word = user_words[0]
            start_positions = [i for i, word in enumerate(ai_words) if word == first_word]
            
            for start_pos in start_positions:
                matches = 0
                for j, user_word in enumerate(user_words):
                    if start_pos + j < len(ai_words):
                        ai_word = ai_words[start_pos + j]
                        # Allow minor variations
                        if user_word == ai_word or (len(user_word) > 3 and len(ai_word) > 3 and 
                                                    user_word[:3] == ai_word[:3]):
                            matches += 1
                        else:
                            break
                
                if matches >= len(user_words) * 0.7:  # 70% threshold
                    logger.info(f"[RELAY_DETECT] Sequential match found: {matches}/{len(user_words)} words")
                    return True
        
        # 3. SLIDING WINDOW CHECK
        # Check if user input matches any continuous portion of AI response
        if len(user_words) >= 3:
            user_text = ' '.join(user_words)
            
            # Try different window sizes
            for window_size in range(len(user_words), len(user_words) + 3):
                if window_size > len(ai_words):
                    break
                    
                for i in range(len(ai_words) - window_size + 1):
                    window_text = ' '.join(ai_words[i:i + window_size])
                    
                    # Calculate similarity
                    common = set(user_words) & set(window_text.split())
                    if len(common) >= len(user_words) * 0.8:  # 80% word overlap
                        logger.info(f"[RELAY_DETECT] Sliding window match at position {i}")
                        return True
        
        # 4. KEY PHRASE DETECTION
        # Extract important phrases (2-3 word combinations)
        def extract_key_phrases(text):
            words = text.split()
            phrases = []
            
            # 2-word phrases
            for i in range(len(words) - 1):
                if len(words[i]) > 3 and len(words[i+1]) > 3:
                    phrases.append(f"{words[i]} {words[i+1]}")
            
            # 3-word phrases
            for i in range(len(words) - 2):
                if len(words[i]) > 3 and len(words[i+1]) > 2 and len(words[i+2]) > 3:
                    phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")
            
            return phrases
        
        user_phrases = extract_key_phrases(user_normalized)
        ai_phrases = extract_key_phrases(ai_normalized)
        
        if user_phrases and ai_phrases:
            common_phrases = set(user_phrases) & set(ai_phrases)
            if len(common_phrases) >= 1:  # At least one key phrase match
                logger.info(f"[RELAY_DETECT] Key phrase match: {common_phrases}")
                return True
        
        # 5. CONTEXTUAL PATTERNS
        # Check for relay indicators in speech
        relay_patterns = [
            (r'^(so|well|basically|yeah|yes|right)\s+(.+)', 2),
            (r'^(it[\'s]?\s+about|it[\'s]?\s+regarding)\s+(.+)', 2),
            (r'^(you said|you mentioned)\s+(.+)', 2),
            (r'^(.+)\s+(right|correct|exactly)$', 1),
        ]
        
        for pattern, group_num in relay_patterns:
            match = re.match(pattern, user_lower)
            if match:
                content = match.group(group_num).strip()
                if content and len(content) > 5:
                    # Check if the content after pattern matches AI response
                    if content in ai_lower or any(phrase in ai_lower for phrase in content.split() if len(phrase) > 4):
                        logger.info(f"[RELAY_DETECT] Contextual pattern match: {pattern}")
                        return True
        
        # 6. COMPLETION DETECTION
        # Check if user is completing a sentence from AI
        ai_sentences = re.split(r'[.!?]', ai_lower)
        for sentence in ai_sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and len(user_normalized) > 5:
                # Check if user input completes or continues the sentence
                if (sentence.endswith(user_normalized[:20]) or 
                    user_normalized.startswith(sentence[-20:])):
                    logger.info(f"[RELAY_DETECT] Sentence completion detected")
                    return True
        
        # 7. TOPIC WORD ANALYSIS
        # Extract topic-specific words (excluding common words)
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does',
            'it', 'this', 'that', 'these', 'those', 'very', 'more', 'most', 'some', 'any'
        }
        
        user_topic_words = [w for w in user_words if len(w) > 3 and w not in common_words]
        ai_topic_words = [w for w in ai_words if len(w) > 3 and w not in common_words]
        
        if user_topic_words and ai_topic_words:
            topic_overlap = set(user_topic_words) & set(ai_topic_words)
            
            # If most topic words overlap, likely a relay
            if len(topic_overlap) >= len(user_topic_words) * 0.6:
                logger.info(f"[RELAY_DETECT] Topic word overlap: {topic_overlap}")
                return True
        
        # 8. QUESTION HANDLING
        # Special handling for questions
        is_question = user_lower.endswith('?') or any(
            user_lower.startswith(q) for q in ['what', 'how', 'why', 'when', 'where', 'who', 'can']
        )
        
        if is_question:
            # For questions, require higher overlap threshold
            question_words = set(user_words) - common_words
            ai_words_set = set(ai_words) - common_words
            
            overlap = question_words & ai_words_set
            if question_words and len(overlap) >= len(question_words) * 0.8:
                # High overlap in question - might be asking for clarification
                logger.info(f"[RELAY_DETECT] Question with high overlap - treating as NEW")
                return False  # Questions about same topic are NEW, not relays
        
        # Log the decision details
        logger.info(f"Context Detection - Words: {len(user_topic_words) if user_topic_words else 0}, "
                   f"Phrases: {len(user_phrases) if user_phrases else 0}, "
                   f"Question: {is_question}, Decision: NEW")
        
        return False

    def _generate_common_variations(self, text):
        """Generate common speech recognition variations"""
        variations = [text]
        
        # Common substitutions
        substitutions = {
            'cyprus': ['cypress'],
            'cypress': ['cyprus'],
            'qa': ['q a', 'quality assurance'],
            'qc': ['q c', 'quality control'],
            'versus': ['vs', 'v s', 'compared to'],
            'vs': ['versus', 'v s'],
            'to': ['2', 'too'],
            'for': ['4', 'four'],
            'ate': ['8', 'eight'],
        }
        
        words = text.split()
        for i, word in enumerate(words):
            if word in substitutions:
                for sub in substitutions[word]:
                    new_words = words[:i] + sub.split() + words[i+1:]
                    variations.append(' '.join(new_words))
        
        return variations
    
    def _are_words_similar(self, word1, word2):
        """Check if two words are similar (handles typos/variations)"""
        # Exact match
        if word1 == word2:
            return True
        
        # Very short words must match exactly
        if len(word1) <= 3 or len(word2) <= 3:
            return False
        
        # Check for common variations
        variations = {
            'cypress': 'cyprus',
            'cyprus': 'cypress',
            'selenium': 'salenium',
            'quality': 'qualty',
        }
        
        if word1 in variations and variations[word1] == word2:
            return True
        if word2 in variations and variations[word2] == word1:
            return True
        
        # Check for singular/plural
        if word1 + 's' == word2 or word2 + 's' == word1:
            return True
        
        # Levenshtein distance for typos (if words are similar length)
        if abs(len(word1) - len(word2)) <= 1:
            distance = sum(a != b for a, b in zip(word1, word2))
            return distance <= 1
        
        return False
    
    def _calculate_similarity_ratio(self, text1, text2):
        """Calculate similarity ratio between two texts"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _extract_key_phrases(self, text):
        """Extract key phrases from text"""
        words = text.split()
        phrases = []
        
        # Common words to skip
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        
        # Extract noun phrases and important combinations
        for i in range(len(words) - 1):
            if len(words[i]) > 3 and len(words[i+1]) > 3:
                phrases.append(f"{words[i]} {words[i+1]}")
        
        # Also include important single words
        important_words = [w for w in words if len(w) > 4 and w not in common_words]
        phrases.extend(important_words)
        
        return phrases

    def _trigger_tts_if_needed(self, response: str):
        """Single point TTS trigger - only place where TTS is activated"""
        start_time = time.time()
        logger.info(f"[TTS_TRIGGER_START] Response length: {len(response) if response else 0}")
        
        if not response or len(response.strip()) <= 10:
            logger.info(f"[TTS_TRIGGER] Response too short or empty - skipping")
            return
            
        gv = self.conversation.context
        if not gv.continuous_read:
            return
            
        # Check if this is an initial/welcome message we should skip reading
        skip_reading = (
            "Welcome to Transcribe" in response or 
            "👋" in response or
            "Hello, V. You are awesome" in response or
            "light hearted banter" in response or
            "light banter" in response
        )
        
        if skip_reading:
            return
            
        # Only trigger if this is a new response (prevent duplicates)
        if response != gv.last_spoken_response:
            logger.info(f"[TTS_TRIGGER] New response detected - triggering TTS")
            logger.info(f"[TTS_TRIGGER] Setting last_spoken_response")
            gv.last_spoken_response = response
            logger.info(f"[TTS_TRIGGER] Setting read_response = True")
            gv.set_read_response(True)
            logger.info(f"[TTS_TRIGGER] Triggering speech_text_available event")
            gv.audio_player_var.speech_text_available.set()
            elapsed = time.time() - start_time
            logger.info(f"[TTS_TRIGGER_END] TTS triggered successfully - Time: {elapsed:.3f}s")

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

    def _get_llm_response(self, messages, temperature, timeout) -> str:
        """Send a request to the LLM and process the streaming response."""
        self.streaming_complete.clear()
        with duration.Duration(name='OpenAI Chat Completion', screen=False):
            multi_turn_response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                timeout=timeout,
                stream=True
            )

            collected_messages = ""
            for chunk in multi_turn_response:
                chunk_message = chunk.choices[0].delta  # extract the message
                if chunk_message.content:
                    message_text = chunk_message.content
                    collected_messages += message_text
                    self._update_conversation(persona=constants.PERSONA_ASSISTANT,
                                              response=collected_messages,
                                              update_previous=True)
            # Mark streaming as complete immediately
            self.streaming_complete.set()
            return collected_messages

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

        try:
            chat_inference_provider = self.config['General']['chat_inference_provider']
            settings_section = self._get_settings_section(chat_inference_provider)
            api_key, base_url, model = self._get_api_settings(settings_section)

            if not utilities.is_api_key_valid(api_key=api_key, base_url=base_url, model=model):
                return None

            timeout, temperature = self._get_openai_settings()
            multiturn_prompt_content = self.conversation.get_merged_conversation_response(
                length=constants.MAX_TRANSCRIPTION_PHRASES_FOR_LLM)
            
            # Handle case where conversation ID might be None
            if multiturn_prompt_content and len(multiturn_prompt_content) > 0:
                last_item = multiturn_prompt_content[-1]
                if len(last_item) > 2 and last_item[2] is not None:
                    last_convo_id = int(last_item[2])
                else:
                    logger.warning("Conversation ID is None, using default")
                    last_convo_id = -1
            else:
                logger.warning("No conversation content available")
                return None
                
            multiturn_prompt_api_message = prompts.create_multiturn_prompt(multiturn_prompt_content)
            collected_messages = self._get_llm_response(multiturn_prompt_api_message, temperature, timeout)
            self._insert_response_in_db(last_convo_id, collected_messages)

        except Exception as e:
            logger.error(f"Error in generate_response_from_transcript_no_check: {e}")
            print(f'Error getting response from LLM: {e}')
            return None

        self._save_response_to_file(collected_messages)
        
        # CRITICAL: Track response BEFORE triggering TTS so relay detection works
        if collected_messages:
            self.last_ai_response = collected_messages
            self.last_ai_response_time = datetime.datetime.utcnow()
            logger.info(f"[RESPONSE_TRACKING] Saved AI response for relay detection: '{collected_messages[:50]}...'")
            
        # SINGLE TTS TRIGGER POINT - only place TTS is triggered
        self._trigger_tts_if_needed(collected_messages)
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
        
        Enhanced with voice identification and global relay tracking to prevent duplicate responses.
        """
        logger.info("generate_response_from_transcript called")
        
        if not self.enabled:
            return ''
        
        # Check global relay state first
        import datetime
        current_time = datetime.datetime.utcnow()
        
        # Reset relay detection if enough time has passed
        if (GPTResponder._relay_detected and 
            GPTResponder._relay_detection_time and
            (current_time - GPTResponder._relay_detection_time).total_seconds() > GPTResponder._relay_reset_interval):
            logger.info(f"Resetting global relay state after {GPTResponder._relay_reset_interval} seconds")
            GPTResponder._relay_detected = False
            GPTResponder._relay_detection_time = None
        
        # If relay was recently detected globally, skip
        if GPTResponder._relay_detected:
            logger.info("Global relay state active - skipping response generation")
            return ''
        
        # Check if voice identification is enabled
        voice_id_config = self.config['General'].get('voice_identification_enabled', 'No')
        voice_id_enabled = voice_id_config in [True, 'Yes', 'yes', 'TRUE', 'true', 1]
        
        voice_response_config = self.config['General'].get('voice_based_response_control', 'Yes')
        voice_based_response = voice_response_config in [True, 'Yes', 'yes', 'TRUE', 'true', 1]
        
        # Get the most recent user input and check speaker information
        recent_conversation = self.conversation.get_conversation(sources=['You', 'Unknown Speaker', 'primary_user (unconfirmed)'], length=1)
        
        # Extract speaker info and text content
        speaker_identified = 'You'  # Default to primary user
        user_text = ""
        
        if recent_conversation:
            # Check speaker type - could be "You", "Unknown Speaker", or "primary_user (unconfirmed)"
            if "Unknown Speaker:" in recent_conversation:
                speaker_identified = 'Unknown Speaker'
                # Extract text after "Unknown Speaker: ["
                user_text = recent_conversation.split("Unknown Speaker:", 1)[1].strip()
            elif "(unconfirmed):" in recent_conversation:
                # Handle unconfirmed primary user
                speaker_identified = 'Unknown Speaker'  # Treat as unknown for response logic
                # Extract text after the speaker name
                colon_pos = recent_conversation.find(":")
                if colon_pos > 0:
                    user_text = recent_conversation[colon_pos + 1:].strip()
                else:
                    user_text = recent_conversation
            else:
                # Confirmed primary user
                speaker_identified = 'You'
                # Extract text after "You: ["
                user_text = recent_conversation.split("You:", 1)[1].strip()
            
            # Remove brackets and voice info annotations
            if user_text.startswith("[") and "]" in user_text:
                end_bracket = user_text.find("]")
                user_text = user_text[1:end_bracket].strip()
                
            logger.info(f"[VOICE_ID] Speaker identified as: '{speaker_identified}'")
            logger.info(f"[VOICE_ID] Text content: '{user_text[:50]}...'")
        
        # Voice-based decision logic
        if voice_id_enabled and voice_based_response:
            if speaker_identified == 'Unknown Speaker':
                # Unknown speaker (colleague) - always generate response
                logger.info("[VOICE_ID] Unknown speaker detected (colleague) - generating response")
                response = self.generate_response_from_transcript_no_check()
                return response
            elif speaker_identified == 'You':
                # Primary user - check for relay
                logger.info("[VOICE_ID] Primary user detected - checking for relay")
                # Continue with relay detection below
            else:
                logger.warning(f"[VOICE_ID] Unexpected speaker: {speaker_identified}")
        elif voice_id_enabled:
            logger.info(f"[VOICE_ID] Voice ID enabled but response control disabled - using standard logic")
        
        # Check if user is relaying our previous response (only for primary user)
        if user_text and self._is_user_relaying_response(user_text):
            logger.info(f"User appears to be relaying previous AI response - skipping new response generation")
            logger.info(f"User said: '{user_text}'")
            logger.info(f"AI last said: '{self.last_ai_response[:100]}...'")
            
            # Set global relay state
            GPTResponder._relay_detected = True
            GPTResponder._relay_detection_time = current_time
            logger.info("Set global relay detection state")
            
            return ''
        
        # Generate new response (tracking is now done inside the method)
        response = self.generate_response_from_transcript_no_check()
        return response
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
                self.streaming_complete.set()

        except Exception as exception:
            print('Error when attempting to get a response from LLM.')
            print(exception)
            logger.error('Error when attempting to get a response from LLM.')
            logger.exception(exception)
            return prompts.INITIAL_RESPONSE

        processed_response = collected_messages

        self._save_response_to_file(processed_response)
        
        # CRITICAL: Track response BEFORE triggering TTS so relay detection works
        if processed_response:
            self.last_ai_response = processed_response
            self.last_ai_response_time = datetime.datetime.utcnow()
            logger.info(f"[RESPONSE_TRACKING] Saved AI response for relay detection: '{processed_response[:50]}...'")
            
        # SINGLE TTS TRIGGER POINT - also for selected text responses
        self._trigger_tts_if_needed(processed_response)
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
                # Get current transcript to check for duplicates
                current_transcript = transcriber.get_transcript()
                
                # Only respond if this is a new transcript we haven't responded to
                if current_transcript != self.last_responded_transcript:
                    start_time = time.time()

                    transcriber.transcript_changed_event.clear()

                    # Do processing only if LLM transcription is enabled
                    if self.enabled:
                        # Check if inverted voice response is enabled
                        inverted_voice = self.config.get('General', {}).get('inverted_voice_response', False)
                        speaker_id = getattr(transcriber, 'last_speaker_id', 'unknown')
                        confidence = getattr(transcriber, 'last_speaker_confidence', 0.0)
                        
                        # Implement inverted logic
                        should_respond = True
                        if inverted_voice:
                            # With inverted logic: respond to unknown speakers, NOT to primary user
                            if speaker_id == 'primary_user' and confidence >= 0.75:
                                should_respond = False
                                logger.info(f"[INVERTED] Not responding to primary user (confidence: {confidence:.2f})")
                            elif speaker_id == 'primary_user' and confidence < 0.75:
                                should_respond = True
                                logger.info(f"[INVERTED] Responding - primary_user but LOW confidence: {confidence:.2f}")
                            else:
                                should_respond = True
                                logger.info(f"[INVERTED] Responding to unknown speaker (confidence: {confidence:.2f})")
                        
                        if should_respond:
                            self.generate_response_from_transcript()
                            self.last_responded_transcript = current_transcript
                        else:
                            # Still mark as processed to avoid re-checking
                            self.last_responded_transcript = current_transcript

                    end_time = time.time()  # Measure end time
                    execution_time = end_time - start_time  # Calculate time to execute the function

                    remaining_time = self.llm_response_interval - execution_time
                    if remaining_time > 0:
                        # print(f'llm_response_interval: {self.llm_response_interval}, execution time: {execution_time}')
                        # print(f'Sleeping for a response for duration: {remaining_time}')
                        time.sleep(remaining_time)
                else:
                    # Same transcript - just clear the event
                    transcriber.transcript_changed_event.clear()
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


class OpenAIResponder(GPTResponder):
    """Uses OpenAI for Chat Inference"""

    def __init__(self,
                 config: dict,
                 convo: conversation.Conversation,
                 response_file_name: str,
                 save_to_file: bool = False,
                 base_url: str = None):
        logger.info(OpenAIResponder.__name__)
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
