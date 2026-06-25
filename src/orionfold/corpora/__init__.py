"""Corpus enrichment — derive rich source records (title/class/excerpt) from the bench examples that
flatten a corpus's sources into their ``input_text``. Read-only and derived; never persisted."""

from orionfold.corpora.sources import enrich_corpus_sources, parse_retrieved_sources

__all__ = ["enrich_corpus_sources", "parse_retrieved_sources"]
