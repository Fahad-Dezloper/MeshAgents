#!/bin/bash
# Scores the checkout after both sessions with the relay checker.
mkdir -p /logs/verifier
python3 -B /tests/score.py R3
