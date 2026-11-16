"""
experiments/tasks.py - Cognitive Task Generator for Baseline, Interruption, and Recovery
Generates equivalent difficulty questions for Level 1 (Easy), Level 2 (Medium), Level 3 (Difficult).
Guarantees distinct question sets between baseline and recovery to eliminate rehearsal bias.
"""

import random
from typing import List, Dict, Any

def generate_easy_questions() -> List[Dict[str, Any]]:
    """Generates Level 1 questions (Basic arithmetic and straightforward logic)."""
    pool = [
        {"prompt": "Calculate: 17 + 28", "options": ["43", "45", "47", "55"], "answer": "45"},
        {"prompt": "Calculate: 63 - 27", "options": ["34", "36", "38", "46"], "answer": "36"},
        {"prompt": "What is the next number: 4, 8, 12, 16, ?", "options": ["18", "20", "22", "24"], "answer": "20"},
        {"prompt": "Calculate: 8 * 7", "options": ["54", "56", "58", "64"], "answer": "56"},
        {"prompt": "Calculate: 84 / 4", "options": ["19", "21", "22", "24"], "answer": "21"},
        {"prompt": "What is the next number: 50, 45, 40, 35, ?", "options": ["25", "30", "32", "33"], "answer": "30"},
        {"prompt": "Calculate: 19 + 34", "options": ["51", "52", "53", "55"], "answer": "53"},
        {"prompt": "Calculate: 72 - 38", "options": ["32", "34", "36", "44"], "answer": "34"},
        {"prompt": "What is the next number: 3, 6, 9, 12, ?", "options": ["14", "15", "16", "18"], "answer": "15"},
        {"prompt": "Calculate: 9 * 6", "options": ["52", "54", "56", "63"], "answer": "54"},
    ]
    random.shuffle(pool)
    return pool

def generate_medium_questions() -> List[Dict[str, Any]]:
    """Generates Level 2 questions (Multi-step arithmetic, order of operations, pattern deduction)."""
    pool = [
        {"prompt": "Solve: (7 * 8) - 19", "options": ["35", "37", "39", "47"], "answer": "37"},
        {"prompt": "Next number in sequence: 3, 7, 15, 31, ?", "options": ["47", "55", "63", "64"], "answer": "63"},
        {"prompt": "Solve for x: 3x + 14 = 41", "options": ["7", "8", "9", "11"], "answer": "9"},
        {"prompt": "Solve: (96 / 6) + (5 * 4)", "options": ["34", "36", "38", "40"], "answer": "36"},
        {"prompt": "Next number in sequence: 2, 6, 18, 54, ?", "options": ["108", "144", "162", "180"], "answer": "162"},
        {"prompt": "If a shirt costs $40 after a 20% discount, what was the original price?", "options": ["$48", "$50", "$52", "$60"], "answer": "$50"},
        {"prompt": "Solve: (12 * 4) - (36 / 3)", "options": ["34", "36", "38", "40"], "answer": "36"},
        {"prompt": "Next number in sequence: 5, 11, 23, 47, ?", "options": ["91", "95", "96", "99"], "answer": "95"},
        {"prompt": "Solve for y: 4y - 15 = 45", "options": ["12", "15", "18", "20"], "answer": "15"},
        {"prompt": "Solve: (8 * 9) - (48 / 6)", "options": ["62", "64", "66", "72"], "answer": "64"},
    ]
    random.shuffle(pool)
    return pool

def generate_difficult_questions() -> List[Dict[str, Any]]:
    """Generates Level 3 questions (Nested logic, modular arithmetic, algebra, analytical deductions)."""
    pool = [
        {"prompt": "Solve: (14 * 6) + (108 / 12) - (4 ** 2)", "options": ["75", "77", "79", "81"], "answer": "77"},
        {"prompt": "Sequence: 2, 3, 7, 16, 32, ? (Differences: 1, 4, 9, 16, ...)", "options": ["55", "57", "64", "68"], "answer": "57"},
        {"prompt": "Solve for x: 2(3x - 4) = 4x + 18", "options": ["11", "12", "13", "14"], "answer": "13"},
        {"prompt": "Evaluate: (17 * 5) - (84 / 7) + (13 * 3)", "options": ["110", "112", "114", "116"], "answer": "112"},
        {"prompt": "Sequence: 3, 5, 9, 17, 33, ? (Rule: 2n - 1)", "options": ["63", "65", "67", "69"], "answer": "65"},
        {"prompt": "If 5 machines make 5 widgets in 5 minutes, how many minutes do 100 machines need to make 100 widgets?", "options": ["5", "20", "50", "100"], "answer": "5"},
        {"prompt": "Solve for k: 3(2k + 5) - 4 = 5(k + 4) + 3", "options": ["10", "12", "14", "16"], "answer": "12"},
        {"prompt": "Sequence: 1, 4, 13, 40, 121, ? (Rule: 3n + 1)", "options": ["324", "364", "368", "372"], "answer": "364"},
        {"prompt": "Evaluate: 15% of 240 plus 25% of 160", "options": ["72", "76", "78", "80"], "answer": "76"},
        {"prompt": "If a triangle has sides 13, 14, 15, what is its semiperimeter?", "options": ["20", "21", "22", "24"], "answer": "21"},
    ]
    random.shuffle(pool)
    return pool

def get_task_sets(complexity: str, count: int = 4) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Returns two disjoint question sets (baseline, recovery) of equivalent difficulty.
    Guarantees baseline and recovery do not share questions.
    """
    if complexity == "Easy":
        all_q = generate_easy_questions()
    elif complexity == "Medium":
        all_q = generate_medium_questions()
    else:
        all_q = generate_difficult_questions()

    baseline_set = all_q[:count]
    recovery_set = all_q[count:count * 2]
    return baseline_set, recovery_set

def generate_memory_challenge() -> Dict[str, Any]:
    """
    Generates a memory challenge for the interruption phase.
    Contains a set of tokens to memorize, followed by distractor cognitive tasks and recall questions.
    """
    token_pools = [
        {"tokens": ["DELTA", "74", "ORION", "19", "NEXUS", "83"], "target_pos": 3, "target_token": "ORION"},
        {"tokens": ["ALPHA", "92", "VORTEX", "41", "CYPHER", "68"], "target_pos": 4, "target_token": "41"},
        {"tokens": ["SIGMA", "35", "COSMOS", "88", "ZENITH", "12"], "target_pos": 5, "target_token": "ZENITH"},
        {"tokens": ["TITAN", "58", "PULSAR", "27", "STELLA", "94"], "target_pos": 2, "target_token": "58"},
        {"tokens": ["AURORA", "63", "VECTOR", "71", "QUANTUM", "39"], "target_pos": 1, "target_token": "AURORA"},
    ]
    selected = random.choice(token_pools)

    # 2 secondary arithmetic distractors during interruption to prevent pure rehearsal
    distractors = [
        {"question": "Quick check: 13 + 18 = ?", "options": ["29", "31", "32", "33"], "answer": "31"},
        {"question": "Quick check: 45 / 5 = ?", "options": ["7", "8", "9", "11"], "answer": "9"},
    ]

    recall_options = [selected["target_token"]]
    other_tokens = [t for t in ["ALPHA", "DELTA", "SIGMA", "TITAN", "AURORA", "27", "41", "74", "88", "94", "VORTEX", "ORION"] if t != selected["target_token"]]
    random.shuffle(other_tokens)
    recall_options.extend(other_tokens[:3])
    random.shuffle(recall_options)

    return {
        "tokens": selected["tokens"],
        "target_position": selected["target_pos"],
        "target_token": selected["target_token"],
        "distractors": distractors,
        "recall_prompt": f"Which token was at Position {selected['target_pos']} in the sequence?",
        "recall_options": recall_options
    }

