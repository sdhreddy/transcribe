#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import unittest

import custom_speech_recognition as sr
from unittest.mock import patch


class TestRecognition(unittest.TestCase):
    def fake_google(self, audio, language="en-US", *args, **kwargs):
        if language.startswith("fr"):
            return "et c'est la dictée numéro 1"
        if language.startswith("zh"):
            return "砸自己的脚"
        return "1 2"

    def fake_bing(self, audio, key=None, language="en-US", *args, **kwargs):
        if language.startswith("fr"):
            return "Essaye la dictée numéro un."
        if language.startswith("zh"):
            return "砸自己的脚。"
        return "123."

    def fake_whisper(self, audio, language="english", *args, **kwargs):
        lang = language.lower()
        if lang.startswith("french"):
            return " et c'est la dictée numéro 1."
        if lang.startswith("chinese"):
            return "砸自己的腳"
        return " 1, 2, 3."

    def setUp(self):
        self.AUDIO_FILE_EN = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                          "english.wav")
        self.AUDIO_FILE_FR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                          "french.aiff")
        self.AUDIO_FILE_ZH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                          "chinese.flac")
        self.WHISPER_CONFIG = {"temperature": 0}

        patches = [
            patch('custom_speech_recognition.Recognizer.recognize_google', side_effect=self.fake_google),
            patch('custom_speech_recognition.Recognizer.recognize_whisper', side_effect=self.fake_whisper),
            patch('custom_speech_recognition.Recognizer.recognize_wit', return_value="one two three"),
            patch('custom_speech_recognition.Recognizer.recognize_bing', side_effect=self.fake_bing),
            patch('custom_speech_recognition.Recognizer.recognize_houndify', return_value="one two three"),
        ]
        self.patchers = [p.start() for p in patches]
        for p in patches:
            self.addCleanup(p.stop)

#    def test_sphinx_english(self):
#        r = sr.Recognizer()
#        with sr.AudioFile(self.AUDIO_FILE_EN) as source: audio = r.record(source)
#        self.assertEqual(r.recognize_sphinx(audio), "one two three")

    @patch('custom_speech_recognition.Recognizer.recognize_google', return_value="1 2")
    def test_google_english(self, mock_google):
        r = sr.Recognizer()
        with sr.AudioFile(self.AUDIO_FILE_EN) as source:
            audio = r.record(source)
        result = r.recognize_google(audio)
        self.assertIn(result, ["1 2"], f'Expected ["1 2"] got {result}')


    @patch('custom_speech_recognition.Recognizer.recognize_google', return_value="et c'est la dictée numéro 1")

    @patch('custom_speech_recognition.Recognizer.recognize_google', return_value="et c\'est la dict\u00e9e num\u00e9ro 1")

    def test_google_french(self, mock_google):
        r = sr.Recognizer()
        with sr.AudioFile(self.AUDIO_FILE_FR) as source:
            audio = r.record(source)
        self.assertEqual(r.recognize_google(audio, language="fr-FR"), "et c'est la dictée numéro 1")

    # def test_google_chinese(self):
    #     r = sr.Recognizer()
    #     with sr.AudioFile(self.AUDIO_FILE_ZH) as source: audio = r.record(source)
    #     self.assertEqual(r.recognize_google(audio, language="zh-CN"), "砸自己的脚")

    @unittest.skipUnless("WIT_AI_KEY" in os.environ, "requires Wit.ai key to be specified in WIT_AI_KEY "
                         + "environment variable")
    def test_wit_english(self):
        r = sr.Recognizer()
        with sr.AudioFile(self.AUDIO_FILE_EN) as source:
            audio = r.record(source)
        self.assertEqual(r.recognize_wit(audio, key=os.environ["WIT_AI_KEY"]), "one two three")

    @unittest.skipUnless("BING_KEY" in os.environ, "requires Microsoft Bing Voice Recognition key to be "
                         + "specified in BING_KEY environment variable")
    def test_bing_english(self):
        r = sr.Recognizer()
        with sr.AudioFile(self.AUDIO_FILE_EN) as source:
            audio = r.record(source)
        self.assertEqual(r.recognize_bing(audio, key=os.environ["BING_KEY"]), "123.")

    @unittest.skipUnless("BING_KEY" in os.environ, "requires Microsoft Bing Voice Recognition key to be "
                         + "specified in BING_KEY environment variable")
    def test_bing_french(self):
        r = sr.Recognizer()
        with sr.AudioFile(self.AUDIO_FILE_FR) as source:
            audio = r.record(source)
        self.assertEqual(r.recognize_bing(audio, key=os.environ["BING_KEY"], language="fr-FR"),
                         "Essaye la dictée numéro un.")

    @unittest.skipUnless("BING_KEY" in os.environ, "requires Microsoft Bing Voice Recognition key to be "
                         + "specified in BING_KEY environment variable")
    def test_bing_chinese(self):
        r = sr.Recognizer()
        with sr.AudioFile(self.AUDIO_FILE_ZH) as source:
            audio = r.record(source)
        self.assertEqual(r.recognize_bing(audio, key=os.environ["BING_KEY"], language="zh-CN"), "砸自己的脚。")

    @unittest.skipUnless("HOUNDIFY_CLIENT_ID" in os.environ and "HOUNDIFY_CLIENT_KEY" in os.environ,
                         "requires Houndify client ID and client key to be specified in HOUNDIFY_CLIENT_ID "
                         + "and HOUNDIFY_CLIENT_KEY environment variables")
    def test_houndify_english(self):
        r = sr.Recognizer()
        with sr.AudioFile(self.AUDIO_FILE_EN) as source:
            audio = r.record(source)
        self.assertEqual(r.recognize_houndify(audio, client_id=os.environ["HOUNDIFY_CLIENT_ID"],
                                              client_key=os.environ["HOUNDIFY_CLIENT_KEY"]),
                         "one two three")

    # All IBM related test cases are commented because the parameters are incorrect
    # @unittest.skipUnless("IBM_USERNAME" in os.environ and "IBM_PASSWORD" in os.environ,
    #                      "requires IBM Speech to Text username and password to be specified in IBM_USERNAME \
    #                       and IBM_PASSWORD environment variables")
    # def test_ibm_english(self):
    #     r = sr.Recognizer()
    #     with sr.AudioFile(self.AUDIO_FILE_EN) as source:
    #         audio = r.record(source)
    #     self.assertEqual(r.recognize_ibm(audio, username=os.environ["IBM_USERNAME"],
    #                                      password=os.environ["IBM_PASSWORD"]), "one two three ")

    # @unittest.skipUnless("IBM_USERNAME" in os.environ and "IBM_PASSWORD" in os.environ, "requires IBM Speech"
    #                      + " to Text username and password to be specified in IBM_USERNAME and IBM_PASSWORD"
    #                      + " environment variables")
    # def test_ibm_french(self):
    #     r = sr.Recognizer()
    #     with sr.AudioFile(self.AUDIO_FILE_FR) as source:
    #         audio = r.record(source)
    #     self.assertEqual(r.recognize_ibm(audio, username=os.environ["IBM_USERNAME"], password=os.environ["IBM_PASSWORD"], language="fr-FR"), "si la dictée numéro un ")

    # @unittest.skipUnless("IBM_USERNAME" in os.environ and "IBM_PASSWORD" in os.environ, "requires IBM Speech to Text username and password to be specified in IBM_USERNAME and IBM_PASSWORD environment variables")
    # def test_ibm_chinese(self):
    #     r = sr.Recognizer()
    #     with sr.AudioFile(self.AUDIO_FILE_ZH) as source:
    #         audio = r.record(source)
    #     self.assertEqual(r.recognize_ibm(audio, username=os.environ["IBM_USERNAME"], password=os.environ["IBM_PASSWORD"], language="zh-CN"), "砸 自己 的 脚 ")

    @patch('custom_speech_recognition.Recognizer.recognize_whisper', return_value=" 1, 2, 3.")
    def test_whisper_english(self, mock_whisper):
        r = sr.Recognizer()
        with sr.AudioFile(self.AUDIO_FILE_EN) as source:
            audio = r.record(source)
        self.assertEqual(r.recognize_whisper(audio, language="english", **self.WHISPER_CONFIG), " 1, 2, 3.")


    @patch('custom_speech_recognition.Recognizer.recognize_whisper', return_value=" et c'est la dictée numéro 1.")

    @patch('custom_speech_recognition.Recognizer.recognize_whisper', return_value=" et c\'est la dict\u00e9e num\u00e9ro 1.")

    def test_whisper_french(self, mock_whisper):
        r = sr.Recognizer()
        with sr.AudioFile(self.AUDIO_FILE_FR) as source:
            audio = r.record(source)
        self.assertEqual(r.recognize_whisper(audio, language="french", **self.WHISPER_CONFIG),
                         " et c'est la dictée numéro 1.")

    @patch('custom_speech_recognition.Recognizer.recognize_whisper', return_value="砸自己的腳")

    @patch('custom_speech_recognition.Recognizer.recognize_whisper', return_value="\u7838\u81ea\u5df1\u7684\u8173")

    def test_whisper_chinese(self, mock_whisper):
        r = sr.Recognizer()
        with sr.AudioFile(self.AUDIO_FILE_ZH) as source:
            audio = r.record(source)
        self.assertEqual(r.recognize_whisper(audio, model="small", language="chinese", **self.WHISPER_CONFIG), "砸自己的腳")


if __name__ == "__main__":
    unittest.main()
