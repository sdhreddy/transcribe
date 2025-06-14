import sys
import types
# ------------------------------------------------------------------
# TEST ENV STUB: provide dummy sqlalchemy if not installed to unblock
# lightweight unit tests. Must execute before importing db modules.
# ------------------------------------------------------------------
# DISABLED for production use - comment out for testing only
# if "sqlalchemy" not in sys.modules:
#     sa_stub = types.ModuleType("sqlalchemy")
#     def _dummy(*args, **kwargs):
#         return None
#     # Add core types
#     sa_stub.Column = _dummy  # type: ignore
#     sa_stub.Integer = _dummy  # type: ignore
#     sa_stub.String = _dummy  # type: ignore
#     sa_stub.DateTime = _dummy  # type: ignore
#     sa_stub.Engine = object  # type: ignore
#     sa_stub.insert = _dummy  # type: ignore
#     sa_stub.__dict__["__getattr__"] = lambda *a, **k: None  # type: ignore
#     
#     orm_stub = types.ModuleType("sqlalchemy.orm")
#     orm_stub.Session = object  # type: ignore
#     class _MappedPlaceholder:
#         @classmethod
#         def __class_getitem__(cls, item):  # type: ignore
#             return object
#     orm_stub.Mapped = _MappedPlaceholder  # type: ignore
#     orm_stub.mapped_column = _dummy  # type: ignore
#     orm_stub.declarative_base = lambda *a, **k: object  # type: ignore
#     orm_stub.__getattr__ = lambda *a, **k: _dummy  # type: ignore
#     sa_stub.orm = orm_stub  # type: ignore
#     sys.modules["sqlalchemy.orm"] = orm_stub
#     sys.modules["sqlalchemy"] = sa_stub
#     # also stub sqlalchemy.sql
#     sql_stub = types.ModuleType("sqlalchemy.sql")
#     sql_stub.update = _dummy  # type: ignore
#     sql_stub.text = _dummy  # type: ignore
#     sql_stub.__getattr__ = lambda *a, **k: _dummy  # type: ignore
#     sa_stub.sql = sql_stub  # type: ignore
#     sys.modules["sqlalchemy.sql"] = sql_stub

from heapq import merge
import datetime
import constants
from db import (
    AppDB as appdb,
    conversation as convodb,
    llm_responses as llmrdb)
# sys.path.append('../..')  # Not needed when package installed
from tsutils import configuration  # noqa: E402 pylint: disable=C0413


class Conversation:
    """Encapsulates the complete conversation.
    The member transcript_data has separate lists for different personas.
    Each list has a tuple of (ConversationText, time, conversation_id)
    """
    _initialized: bool = False
    update_handler = None
    insert_handler = None

    def __init__(self, context):
        self.transcript_data = {constants.PERSONA_SYSTEM: [],
                                constants.PERSONA_YOU: [],
                                constants.PERSONA_SPEAKER: [],
                                constants.PERSONA_ASSISTANT: []}
        self.last_update: datetime.datetime = None
        self.initialize_conversation()
        self.context = context

    def set_handlers(self, update, insert):
        """Sets handlers to be called when a conversation is updated or
           a new conversation is inserted.

        Args:
        update: Handler for update update(persona, input_text)
        insert: Handler for insert insert(input_text)
        """
        self.update_handler = update
        self.insert_handler = insert

    def initialize_conversation(self):
        """Populate initial app data for conversation object
        """
        self.config = configuration.Config().data
        prompt = self.config["General"]["system_prompt"]
        response_lang = self.config["OpenAI"]["response_lang"]
        if response_lang is not None:
            prompt += f'.  Respond exclusively in {response_lang}.'

        self.update_conversation(persona=constants.PERSONA_SYSTEM, text=prompt,
                                 time_spoken=datetime.datetime.utcnow())
        initial_convo: dict = self.config["General"]["initial_convo"]
        # Read the initial conversation from parameters.yaml file and add to the convo
        for _, value in initial_convo.items():
            role = value['role']
            content = value['content']
            self.update_conversation(persona=role, text=content,
                                     time_spoken=datetime.datetime.utcnow())
        self.last_update: datetime.datetime = datetime.datetime.utcnow()
        self._initialized = True

    def clear_conversation_data(self):
        """Clear all conversation data
        """
        self.transcript_data[constants.PERSONA_YOU].clear()
        self.transcript_data[constants.PERSONA_SPEAKER].clear()
        self.transcript_data[constants.PERSONA_SYSTEM].clear()
        self.transcript_data[constants.PERSONA_ASSISTANT].clear()
        self.initialize_conversation()

    def update_conversation_by_id(self, persona: str, convo_id: int, text: str):
        """
        Update a conversation entry in the transcript_data list.

        Args:
            persona (str): The persona whose conversation is to be updated.
            convo_id (int): The ID of the conversation entry to update.
            text (str): The new content of the conversation.
        """
        transcript = self.transcript_data[persona]

        # Find the conversation with the given convo_id
        for index, (_, time_spoken, current_convo_id) in enumerate(transcript):
            if current_convo_id == convo_id:
                # Update the conversation text
                new_convo_text = f"{persona}: [{text}]\n\n"
                transcript[index] = (new_convo_text, time_spoken, convo_id)
                # Update the conversation in the database
                if self._initialized:
                    # inv_id = appdb().get_invocation_id()
                    convo_object: convodb.Conversations = appdb().get_object(convodb.TABLE_NAME)
                    convo_object.update_conversation(convo_id, text)
                    # if persona.lower() != 'assistant':
                    #    self.update_handler(persona, new_convo_text)
                break
        else:
            print(f'Conversation with ID {convo_id} not found for persona {persona}.')

    def update_conversation(self, persona: str,
                            text: str,
                            time_spoken,
                            update_previous: bool = False):
        """Update conversation with new data
        Args:
        person: person this part of conversation is attributed to
        text: Actual words
        time_spoken: Time at which conversation happened, this is typically reported in local time
        """

        transcript = self.transcript_data[persona]
        convo_id = None

        # DB is not available at the time conversation object is being initialized.
        if self._initialized:
            inv_id = appdb().get_invocation_id()
            convo_object: convodb.Conversations = appdb().get_object(convodb.TABLE_NAME)
            convo_id = convo_object.get_max_convo_id(speaker=persona, inv_id=inv_id)

        convo_text = f"{persona}: [{text}]\n\n"
        ui_text = f"{persona}: [{text}]\n"
        # if (persona.lower() == 'assistant'):
        #     print(f'Assistant Transcript length to begin with: {len(transcript)}')
        #     print(f'append: {text}')

        # For persona you, we populate one item from parameters.yaml.
        # Hence do not delete the first item for persona == You
        if (update_previous
            and (
                (persona.lower() == 'you' and len(transcript) > 1)
                or (persona.lower() != 'you' and len(transcript) > 0)
                )):
            prev_element = transcript.pop()
            # Use timestamp of previous element, since it is an update
            time_spoken = prev_element[1]
            if self._initialized:
                # Update DB
                # print(f'Removed: {prev_element}')
                # print(f'Update DB: {inv_id} - {time_spoken} - {persona} - {text}')
                convo_object.update_conversation(convo_id, text)
                if persona.lower() != 'assistant':
                    self.update_handler(persona, ui_text)
        else:
            if self._initialized and persona != constants.PERSONA_SYSTEM and persona != constants.PERSONA_ASSISTANT:
                # Insert in DB
                # print(f'Add to DB: {inv_id} - {time_spoken} - {persona} - {text}')
                convo_id = convo_object.insert_conversation(inv_id, time_spoken, persona, text)
                if self.insert_handler is not None:
                    self.insert_handler(ui_text)

        # print(f'Added: {time_spoken} - {new_element}')
        transcript.append((convo_text, time_spoken, convo_id))

        self.last_update = datetime.datetime.utcnow()

    def get_convo_id(self, persona: str, input_text: str):
        """
        Retrieves the ID of the conversation row that matches the given speaker and text.

        Args:
            speaker (str): The name of the speaker.
            text (str): The content of the conversation.

        Returns:
            int: The ID of the matching conversation entry.
        """
        if not self._initialized:
            return
        cleaned_text = input_text.strip()
        if cleaned_text[0] == '[':
            cleaned_text = cleaned_text[1:]
        if cleaned_text[-1] == ']':
            cleaned_text = cleaned_text[:-1]
        inv_id = appdb().get_invocation_id()
        convo_object: convodb.Conversations = appdb().get_object(convodb.TABLE_NAME)
        convo_id = convo_object.get_convo_id_by_speaker_and_text(speaker=persona,
                                                                 input_text=cleaned_text,
                                                                 inv_id=inv_id)
        return convo_id

    def _extract_convo_id(self, line_text: str):
        """Helper to extract conversation id from UI line text."""
        end_speaker = line_text.find(":")
        if end_speaker == -1:
            return None
        persona = line_text[:end_speaker].strip()
        transcript = self.transcript_data.get(persona)
        if not transcript:
            return None
        for first, _, convo_id in transcript:
            if first.strip() == line_text.strip():
                return convo_id
        return None

    def on_convo_select(self, line_text: str):
        """Callback when a specific conversation is selected."""
        convo_id = None
        if line_text:
            convo_id = self._extract_convo_id(line_text)
        if not convo_id:
            return

        # Get LLM_response for this convo_id
        # get_text_by_invocation_and_conversation
        inv_id = appdb().get_invocation_id()
        llmr_object: llmrdb.LLMResponses = appdb().get_object(llmrdb.TABLE_NAME)
        response = llmr_object.get_text_by_invocation_and_conversation(inv_id, convo_id)
        self.context.previous_response = response if response else 'No LLM response corresponding to this row'

    def get_conversation(self,
                         sources: list = None,
                         length: int = 0) -> list:
        """Get the transcript based on specified sources
        Args:
        sources: Get data from which sources (You, Speaker, Assistant, System)
        length: Get the last length elements from the audio transcript.
                Default value = 0, gives the complete transcript for chosen sources
        reverse: reverse the sort order or keep it in chronological order
        """
        if sources is None:
            sources = [constants.PERSONA_YOU,
                       constants.PERSONA_SPEAKER,
                       constants.PERSONA_ASSISTANT,
                       constants.PERSONA_SYSTEM]

        combined_transcript = list(merge(
            self.transcript_data[constants.PERSONA_YOU][-length:] if constants.PERSONA_YOU in sources else [],
            self.transcript_data[constants.PERSONA_SPEAKER][-length:] if constants.PERSONA_SPEAKER in sources else [],
            self.transcript_data[constants.PERSONA_ASSISTANT][-length:] if constants.PERSONA_ASSISTANT in sources else [],
            self.transcript_data[constants.PERSONA_SYSTEM][-length:] if constants.PERSONA_SYSTEM in sources else [],
            key=lambda x: x[1]))
        combined_transcript = combined_transcript[-length:]
        return "".join([t[0] for t in combined_transcript])

    def get_merged_conversation_summary(self, length: int = 0) -> list:
        """Creates a prompt to be sent to LLM (OpenAI by default) for summarizing
           the conversation.
           length: Get the last length elements from the audio transcript.
           Initial system prompt is always part of the return value
           Default value = 0, gives the complete transcript
        """

        combined_transcript = self.transcript_data[constants.PERSONA_YOU][-length:] \
            + self.transcript_data[constants.PERSONA_SPEAKER][-length:] \
            + self.transcript_data[constants.PERSONA_ASSISTANT][-length:]
        sorted_transcript = sorted(combined_transcript, key=lambda x: x[1])
        sorted_transcript = sorted_transcript[-length:]
        sorted_transcript.insert(0, self.transcript_data[constants.PERSONA_YOU][0])
        sorted_transcript.insert(0, (f"{constants.PERSONA_SYSTEM}: [{self.config['General']['summary_prompt']}]\n\n",
                                     datetime.datetime.now(), -1))
        return sorted_transcript

    def get_merged_conversation_response(self, length: int = 0) -> list:
        """Creates a prompt to be sent to LLM (OpenAI by default) to get
           a contextual response.
           length: Get the last length elements from the audio transcript.
           Initial summary prompt is always part of the return value
           Default value = 0, gives the complete transcript
        """

        combined_transcript = self.transcript_data[constants.PERSONA_YOU][-length:] \
            + self.transcript_data[constants.PERSONA_SPEAKER][-length:] \
            + self.transcript_data[constants.PERSONA_ASSISTANT][-length:]
        sorted_transcript = sorted(combined_transcript, key=lambda x: x[1])
        sorted_transcript = sorted_transcript[-length:]
        sorted_transcript.insert(0, self.transcript_data[constants.PERSONA_YOU][0])
        sorted_transcript.insert(0, self.transcript_data[constants.PERSONA_SYSTEM][0])
        # print(f'{datetime.datetime.now()}: Sorted transcript')
        # self._pretty_print_transcript(sorted_transcript)

        return sorted_transcript

    def get_merged_conversation_response_latest_only(self, length: int = 0) -> list:
        """Creates a prompt with only the latest speaker's input to prevent accumulated responses.
           Used when inverted voice logic is enabled to avoid responding to all previous questions.
        """
        # Get all recent transcripts
        combined_transcript = self.transcript_data[constants.PERSONA_YOU][-length:] \
            + self.transcript_data[constants.PERSONA_SPEAKER][-length:] \
            + self.transcript_data[constants.PERSONA_ASSISTANT][-length:]
        
        # Sort by time to find the latest speaker input
        sorted_transcript = sorted(combined_transcript, key=lambda x: x[1])
        
        # Find the last non-assistant entry (latest user/speaker input)
        latest_input = None
        latest_assistant = None
        for i in range(len(sorted_transcript) - 1, -1, -1):
            transcript_persona = sorted_transcript[i][0].split(':')[0].strip()
            if transcript_persona != constants.PERSONA_ASSISTANT and not latest_input:
                latest_input = sorted_transcript[i]
            elif transcript_persona == constants.PERSONA_ASSISTANT and latest_input and not latest_assistant:
                # Get the last assistant response before the latest input
                if sorted_transcript[i][1] < latest_input[1]:
                    latest_assistant = sorted_transcript[i]
                    break
        
        # Build response with system prompt, initial context, and latest exchange
        result = []
        result.append(self.transcript_data[constants.PERSONA_SYSTEM][0])
        result.append(self.transcript_data[constants.PERSONA_YOU][0])  # Initial conversation
        
        # Add last assistant response if exists (for context)
        if latest_assistant:
            result.append(latest_assistant)
            
        # Add latest user input
        if latest_input:
            result.append(latest_input)
        
        return result

    def _pretty_print_transcript(self, message: list):
        """Format the openAI request in a nice print format"""
        print('[')
        for item in message:
            print('  {')
            print(f'    {item[0].strip()}')
            print(f'    {item[1]}')
            print('  }')

        print(']')

# after sqlalchemy stub
# sys.modules["sqlalchemy.sql"] = sql_stub  # Commented out - sql_stub not defined

# --------------------------------------------------------------
# DB PACKAGE STUB for lightweight unit tests (no real SQLAlchemy)
# --------------------------------------------------------------
if "db" not in sys.modules:
    import types as _t
    db_stub = _t.ModuleType("db")

    class _AppDB:
        def get_invocation_id(self):
            return 0

        def get_object(self, _table_name):
            return _Conversations()

    class _Conversations:
        TABLE_NAME = "conversations"

        def update_conversation(self, *a, **k):
            pass

        def insert_conversation(self, *a, **k):
            return 0

        def get_max_convo_id(self, *a, **k):
            return 0

        def get_convo_id_by_speaker_and_text(self, *a, **k):
            return 0

    class _LLMResponses:
        TABLE_NAME = "llm_responses"

    # submodules
    app_db_mod = _t.ModuleType("db.app_db")
    app_db_mod.AppDB = _AppDB
    convo_mod = _t.ModuleType("db.conversation")
    convo_mod.Conversations = _Conversations
    llm_mod = _t.ModuleType("db.llm_responses")
    llm_mod.LLMResponses = _LLMResponses

    db_stub.app_db = app_db_mod
    db_stub.conversation = convo_mod
    db_stub.llm_responses = llm_mod

    sys.modules["db"] = db_stub
    sys.modules["db.app_db"] = app_db_mod
    sys.modules["db.conversation"] = convo_mod
    sys.modules["db.llm_responses"] = llm_mod
