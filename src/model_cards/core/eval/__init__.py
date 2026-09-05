"""Evaluation instruments for model cards: the judge, the screen, and the probes.

Every instrument here is frozen by content: the prompt and the schema hash into an id
that is recorded with each result, so two numbers can only be compared when they were
produced by the same question. Nothing in this package composes a card, and nothing here
runs without an explicit command.
"""
