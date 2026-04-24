"""
Tests for app/core/text.py
"""

from __future__ import annotations

from app.core.text import split_text_into_chunks


class TestSplitTextIntoChunks:
    """Tests for split_text_into_chunks function."""

    def test_empty_text(self):
        """Test splitting empty text."""
        result = split_text_into_chunks("")
        assert result == []

    def test_whitespace_only(self):
        """Test splitting whitespace-only text."""
        result = split_text_into_chunks("   \n\t  ")
        assert result == []

    def test_single_sentence(self):
        """Test splitting single sentence."""
        result = split_text_into_chunks("Hello world.")
        assert result == ["Hello world."]

    def test_multiple_sentences(self):
        """Test splitting multiple sentences."""
        result = split_text_into_chunks("Hello. World. Test.")

        assert len(result) == 1
        assert "Hello" in result[0]
        assert "World" in result[0]
        assert "Test" in result[0]

    def test_sentence_limit(self):
        """Test max_sentences_per_chunk limit."""
        sentences = ". ".join([f"Sentence {i}" for i in range(10)]) + "."
        result = split_text_into_chunks(sentences, max_sentences_per_chunk=3)

        for chunk in result:
            sentence_count = chunk.count(".") + chunk.count("!") + chunk.count("?")
            assert sentence_count <= 3

    def test_character_limit(self):
        """Test max_chunk_chars limit."""
        long_sentence = "A" * 500 + "."
        result = split_text_into_chunks(long_sentence, max_chunk_chars=100)

        for chunk in result:
            assert len(chunk) <= 100

    def test_preserves_punctuation(self):
        """Test that punctuation is preserved."""
        text = "Hello! How are you? I am fine."
        result = split_text_into_chunks(text)

        assert "!" in result[0]
        assert "?" in result[0]
        assert "." in result[0]

    def test_sentence_split_boundaries(self):
        """Test splitting at sentence boundaries."""
        text = "First sentence. Second sentence! Third sentence? Fourth."
        result = split_text_into_chunks(text, max_sentences_per_chunk=2)

        assert len(result) == 2

    def test_very_long_sentence(self):
        """Test handling very long single sentence."""
        text = "A" * 1000 + "."
        result = split_text_into_chunks(text, max_chunk_chars=320)

        for chunk in result:
            assert len(chunk) <= 320

    def test_mixed_length_sentences(self):
        """Test handling mixed length sentences."""
        text = "Short. " + "A" * 500 + ". " + "Another short."
        result = split_text_into_chunks(text, max_chunk_chars=100, max_sentences_per_chunk=1)

        assert len(result) >= 2

    def test_default_parameters(self):
        """Test default parameter values."""
        text = "Test sentence. Another one. Third one. Fourth. Fifth. Sixth."
        result = split_text_into_chunks(text)

        assert len(result) >= 1

    def test_newlines_in_text(self):
        """Test handling text with newlines."""
        text = "First line.\nSecond line.\nThird line."
        result = split_text_into_chunks(text)

        assert len(result) >= 1

    def test_multiple_spaces(self):
        """Test handling text with multiple spaces."""
        text = "Hello.    World.   Test."
        result = split_text_into_chunks(text)

        assert len(result) >= 1

    def test_question_and_exclamation_marks(self):
        """Test splitting at question and exclamation marks."""
        text = "Hello! How are you? I am fine!"
        result = split_text_into_chunks(text, max_sentences_per_chunk=1)

        assert len(result) == 3

    def test_no_punctuation(self):
        """Test handling text without sentence-ending punctuation."""
        text = "No punctuation here"
        result = split_text_into_chunks(text)

        assert result == ["No punctuation here"]

    def test_trailing_whitespace(self):
        """Test handling trailing whitespace."""
        text = "Hello. World.   "
        result = split_text_into_chunks(text)

        assert len(result) >= 1
        for chunk in result:
            assert chunk == chunk.strip()

    def test_text_with_only_whitespace_sentences(self):
        """Test text where sentence split returns empty strings."""
        text = "...   !!!   ???"
        result = split_text_into_chunks(text)

        assert result == ["... !!! ???"]

    def test_long_sentence_exact_boundary_split(self):
        """Test that very long sentences are split at exact character boundaries."""
        text = "A" * 320 + "."
        result = split_text_into_chunks(text, max_chunk_chars=100)

        assert len(result) == 4
        assert len(result[0]) == 100
        assert len(result[1]) == 100
        assert len(result[2]) == 100
        assert len(result[3]) == 21

    def test_long_sentence_split_with_empty_segment(self):
        """Test that empty segments are skipped during long sentence split."""
        text = "A" * 100 + "   " + "B" * 100 + "."
        result = split_text_into_chunks(text, max_chunk_chars=50)

        for chunk in result:
            assert len(chunk) <= 50
            assert chunk.strip() != ""

    def test_long_sentence_with_whitespace_chunk_boundary(self):
        """Test long sentence where chunk boundary falls on whitespace."""
        text = "A" * 50 + " " * 50 + "B" * 50 + "."
        result = split_text_into_chunks(text, max_chunk_chars=50)

        assert len(result) == 3
        assert result[0] == "A" * 50
        assert result[1] == "B" * 50
        assert result[2] == "."

    def test_text_line_40_unreachable(self):
        """Test that line 40 is unreachable - sentences is never empty after split."""
        import re
        sentence_split = re.compile(r"(?<=[.!?])\s+")

        text = "Test text with no punctuation at end"
        stripped = text.strip()
        sentences = [s.strip() for s in sentence_split.split(stripped) if s.strip()]

        assert sentences == ["Test text with no punctuation at end"]

        result = split_text_into_chunks(text)
        assert result == ["Test text with no punctuation at end"]
