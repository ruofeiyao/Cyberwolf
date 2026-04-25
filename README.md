# Cyberwolf

Code, prompts, analysis scripts, and supplementary materials for my undergraduate thesis, *Cyberwolf: Reasoning and Decision-Making in LLM Agents*.

## Overview
This project studies how LLM-based agents make decisions in a simplified text-based Werewolf environment. The thesis examines how agents interpret dialogue, use interaction history, and translate reasoning into action under uncertainty.

## Repository Contents
- `agents/` – agent implementations
- `engine.py` – core game environment
- `prompts.py` – prompt templates and prompt-building logic
- `schemas.py` – output schema definitions
- `analyze_logs.py` and related scripts – analysis utilities
- supplementary materials used in the thesis

## Experimental Setup
- 8 players
- 2 Wolves, 1 Seer, 1 Doctor, 4 Villagers
- paired strategic and neutral prompt conditions
- model: gemini-2.5-flash
- temperature: 0.3

## Thesis
This repository accompanies the thesis submitted to the Department of Cognitive Science at Vassar College.

## Author
Ruofei Yao
