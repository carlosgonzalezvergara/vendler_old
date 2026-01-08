# -*- coding: utf-8 -*-
"""
Aktionsart detector (EN version)
"""
import locale
import logging
import os
import readline
import subprocess
import time
import sys
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Union
import spacy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- EXCEPTION FOR RESTART ---
class RestartAnalysis(Exception):
    """Exception to abort the current analysis and return to the start."""
    pass

# Códigos ANSI para formato
BOLD = '\033[1m'
RESET = '\033[0m'

# --- SPA_CY SETUP ---
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None

# ------------------------- Config -------------------------
LS_SCRIPT = "ls_en.py" 

class Answer(Enum):
    YES = ["yes", "y"]
    NO = ["no", "n"]


class Aktionsart(Enum):
    STATE = "state"
    CAUSATIVE_STATE = "causative state"
    ACHIEVEMENT = "achievement"
    CAUSATIVE_ACHIEVEMENT = "causative achievement"
    SEMELFACTIVE = "semelfactive"
    CAUSATIVE_SEMELFACTIVE = "causative semelfactive"
    ACTIVE_ACCOMPLISHMENT = "active accomplishment"
    CAUSATIVE_ACTIVE_ACCOMPLISHMENT = "causative active accomplishment"
    ACCOMPLISHMENT = "accomplishment"
    CAUSATIVE_ACCOMPLISHMENT = "causative accomplishment"
    ACTIVITY = "activity"
    CAUSATIVE_ACTIVITY = "causative activity"
    PROCESS = "process"
    CAUSATIVE_PROCESS = "causative process"


@dataclass
class Features:
    causative: bool = False
    stative: bool = False
    punctual: bool = False
    telic: bool = False
    dynamic: bool = False


@dataclass
class ClauseData:
    gerund: str = ""
    participle: str = ""
    infinitive: str = "" 
    subject: str = ""
    postverbal: str = ""
    person_number: str = ""
    got_forms: bool = False


# Auxiliaries for English agreement
BE_PRESENT = {
    '1s': "am", '2s': "are", '3s': "is",
    '1p': "are", '2p': "are", '3p': "are"
}

BE_PAST = {
    '1s': "was", '2s': "were", '3s': "was",
    '1p': "were", '2p': "were", '3p': "were"
}

HAVE_PRESENT = {
    '1s': "have", '2s': "have", '3s': "has",
    '1p': "have", '2p': "have", '3p': "have"
}

# --- IRREGULAR VERBS DICTIONARY ---
IRREGULARS = {
    "be": {"ger": "being", "pp": "been"},
    "have": {"ger": "having", "pp": "had"},
    "do": {"ger": "doing", "pp": "done"},
    "go": {"ger": "going", "pp": "gone"},
    "say": {"ger": "saying", "pp": "said"},
    "make": {"ger": "making", "pp": "made"},
    "get": {"ger": "getting", "pp": "gotten"},
    "know": {"ger": "knowing", "pp": "known"},
    "think": {"ger": "thinking", "pp": "thought"},
    "take": {"ger": "taking", "pp": "taken"},
    "see": {"ger": "seeing", "pp": "seen"},
    "come": {"ger": "coming", "pp": "come"},
    "want": {"ger": "wanting", "pp": "wanted"},
    "look": {"ger": "looking", "pp": "looked"},
    "use": {"ger": "using", "pp": "used"},
    "find": {"ger": "finding", "pp": "found"},
    "give": {"ger": "giving", "pp": "given"},
    "tell": {"ger": "telling", "pp": "told"},
    "work": {"ger": "working", "pp": "worked"},
    "call": {"ger": "calling", "pp": "called"},
    "try": {"ger": "trying", "pp": "tried"},
    "ask": {"ger": "asking", "pp": "asked"},
    "need": {"ger": "needing", "pp": "needed"},
    "feel": {"ger": "feeling", "pp": "felt"},
    "become": {"ger": "becoming", "pp": "become"},
    "leave": {"ger": "leaving", "pp": "left"},
    "put": {"ger": "putting", "pp": "put"},
    "mean": {"ger": "meaning", "pp": "meant"},
    "keep": {"ger": "keeping", "pp": "kept"},
    "let": {"ger": "letting", "pp": "let"},
    "begin": {"ger": "beginning", "pp": "begun"},
    "seem": {"ger": "seeming", "pp": "seemed"},
    "help": {"ger": "helping", "pp": "helped"},
    "talk": {"ger": "talking", "pp": "talked"},
    "turn": {"ger": "turning", "pp": "turned"},
    "start": {"ger": "starting", "pp": "started"},
    "show": {"ger": "showing", "pp": "shown"},
    "hear": {"ger": "hearing", "pp": "heard"},
    "play": {"ger": "playing", "pp": "played"},
    "run": {"ger": "running", "pp": "run"},
    "move": {"ger": "moving", "pp": "moved"},
    "live": {"ger": "living", "pp": "lived"},
    "believe": {"ger": "believing", "pp": "believed"},
    "bring": {"ger": "bringing", "pp": "brought"},
    "happen": {"ger": "happening", "pp": "happened"},
    "write": {"ger": "writing", "pp": "written"},
    "sit": {"ger": "sitting", "pp": "sat"},
    "stand": {"ger": "standing", "pp": "stood"},
    "lose": {"ger": "losing", "pp": "lost"},
    "pay": {"ger": "paying", "pp": "paid"},
    "meet": {"ger": "meeting", "pp": "met"},
    "include": {"ger": "including", "pp": "included"},
    "continue": {"ger": "continuing", "pp": "continued"},
    "set": {"ger": "setting", "pp": "set"},
    "learn": {"ger": "learning", "pp": "learned"},
    "change": {"ger": "changing", "pp": "changed"},
    "lead": {"ger": "leading", "pp": "led"},
    "understand": {"ger": "understanding", "pp": "understood"},
    "watch": {"ger": "watching", "pp": "watched"},
    "follow": {"ger": "following", "pp": "followed"},
    "stop": {"ger": "stopping", "pp": "stopped"},
    "create": {"ger": "creating", "pp": "created"},
    "speak": {"ger": "speaking", "pp": "spoken"},
    "read": {"ger": "reading", "pp": "read"},
    "allow": {"ger": "allowing", "pp": "allowed"},
    "add": {"ger": "adding", "pp": "added"},
    "spend": {"ger": "spending", "pp": "spent"},
    "grow": {"ger": "growing", "pp": "grown"},
    "open": {"ger": "opening", "pp": "opened"},
    "walk": {"ger": "walking", "pp": "walked"},
    "win": {"ger": "winning", "pp": "won"},
    "offer": {"ger": "offering", "pp": "offered"},
    "remember": {"ger": "remembering", "pp": "remembered"},
    "love": {"ger": "loving", "pp": "loved"},
    "consider": {"ger": "considering", "pp": "considered"},
    "appear": {"ger": "appearing", "pp": "appeared"},
    "buy": {"ger": "buying", "pp": "bought"},
    "wait": {"ger": "waiting", "pp": "waited"},
    "serve": {"ger": "serving", "pp": "served"},
    "die": {"ger": "dying", "pp": "died"},
    "send": {"ger": "sending", "pp": "sent"},
    "expect": {"ger": "expecting", "pp": "expected"},
    "build": {"ger": "building", "pp": "built"},
    "stay": {"ger": "staying", "pp": "stayed"},
    "fall": {"ger": "falling", "pp": "fallen"},
    "cut": {"ger": "cutting", "pp": "cut"},
    "reach": {"ger": "reaching", "pp": "reached"},
    "kill": {"ger": "killing", "pp": "killed"},
    "remain": {"ger": "remaining", "pp": "remained"},
    "suggest": {"ger": "suggesting", "pp": "suggested"},
    "raise": {"ger": "raising", "pp": "raised"},
    "pass": {"ger": "passing", "pp": "passed"},
    "sell": {"ger": "selling", "pp": "sold"},
    "require": {"ger": "requiring", "pp": "required"},
    "report": {"ger": "reporting", "pp": "reported"},
    "decide": {"ger": "deciding", "pp": "decided"},
    "pull": {"ger": "pulling", "pp": "pulled"},
    "break": {"ger": "breaking", "pp": "broken"},
    "teach": {"ger": "teaching", "pp": "taught"},
    "eat": {"ger": "eating", "pp": "eaten"},
    "drive": {"ger": "driving", "pp": "driven"},
    "drink": {"ger": "drinking", "pp": "drunk"},
    "sing": {"ger": "singing", "pp": "sung"},
    "swim": {"ger": "swimming", "pp": "swum"},
    "fly": {"ger": "flying", "pp": "flown"},
    "draw": {"ger": "drawing", "pp": "drawn"},
    "forget": {"ger": "forgetting", "pp": "forgotten"},
    "hit": {"ger": "hitting", "pp": "hit"},
    "catch": {"ger": "catching", "pp": "caught"},
    "sleep": {"ger": "sleeping", "pp": "slept"},
    "throw": {"ger": "throwing", "pp": "thrown"},
    "wake": {"ger": "waking", "pp": "woken"},
    "wear": {"ger": "wearing", "pp": "worn"},
    "choose": {"ger": "choosing", "pp": "chosen"},
    "hide": {"ger": "hiding", "pp": "hidden"},
}


def set_english_locale():
    english_locales = ['en_US.UTF-8', 'en_GB.UTF-8', 'en.UTF-8', '']
    for loc in english_locales:
        try:
            return locale.setlocale(locale.LC_ALL, loc)
        except locale.Error:
            continue
    return locale.setlocale(locale.LC_ALL, '')


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def restart_message() -> None:
    print("\nIt is not possible to identify the aktionsart of the clause with these parameters.")
    print("Please review your answers carefully.")


def prompt_user(prompt: str) -> str:
    readline.set_startup_hook(lambda: readline.insert_text(""))
    try:
        if "\n" in prompt or len(prompt) > 60:
            print(prompt, end="", flush=True)
            user = input().strip()
        else:
            user = input(prompt).strip()
        
        # --- RESCUE COMMAND ---
        if user == "...":
            raise RestartAnalysis()
            
        return user.encode('utf-8').decode('utf-8')
    finally:
        readline.set_startup_hook()


def yes_no(question: str) -> bool:
    while True:
        try:
            ans = prompt_user(question).lower()
            if ans in Answer.YES.value:
                return True
            elif ans in Answer.NO.value:
                return False
            print("\nPlease answer 'yes (y)' or 'no (n)'.")
        except RestartAnalysis:
            raise
        except Exception as e:
            logging.error(f"Error getting answer: {e}")


def multiple_choice(question: str, options: Sequence[Union[str, Sequence[str]]], suffix: str) -> str:
    while True:
        try:
            ans = prompt_user(f"{question} {suffix}").lower()
            for opt in options:
                if isinstance(opt, Sequence) and not isinstance(opt, str):
                    if ans in opt:
                        return opt[0]
                elif ans == opt:
                    return opt
            print("\nPlease type a valid option.")
        except RestartAnalysis:
            raise
        except Exception as e:
            logging.error(f"Error getting answer: {e}")


# --- AUTOMATIC ANALYSIS FUNCTIONS ---

def generate_english_forms(lemma: str):
    """
    Generates Gerund and Past Participle using dictionary + heuristic rules.
    """
    lemma = lemma.lower().strip()
    
    # 1. Check dictionary
    if lemma in IRREGULARS:
        return IRREGULARS[lemma]["ger"], IRREGULARS[lemma]["pp"]
    
    # 2. Regular Rules
    # Gerund
    if lemma.endswith("ie"):
        ger = lemma[:-2] + "ying" # die -> dying
    elif lemma.endswith("e") and not lemma.endswith("ee"):
        ger = lemma[:-1] + "ing" # make -> making
    else:
        # CONSONANT DOUBLING RULE
        is_cvc = (len(lemma) > 2 
                  and lemma[-1] not in "aeiouwyx" 
                  and lemma[-2] in "aeiou" 
                  and lemma[-3] not in "aeiou")
        
        is_unstressed_ending = lemma.endswith(("er", "en", "el", "it")) 
        
        if is_cvc and not is_unstressed_ending:
             ger = lemma + lemma[-1] + "ing"
        else:
             ger = lemma + "ing"
             
    # Past Participle (Regular)
    if lemma.endswith("e"):
        pp = lemma + "d"
    else:
        # Same doubling logic
        is_cvc = (len(lemma) > 2 
                  and lemma[-1] not in "aeiouwyx" 
                  and lemma[-2] in "aeiou" 
                  and lemma[-3] not in "aeiou")
        
        is_unstressed_ending = lemma.endswith(("er", "en", "el", "it"))

        if is_cvc and not is_unstressed_ending:
             pp = lemma + lemma[-1] + "ed"
        else:
             pp = lemma + "ed"
             
    return ger, pp

def detect_person_number(doc, verb_token, idx):
    """
    Deduces Person/Number based on the Subject found by spaCy.
    """
    subj_token = None
    for token in doc:
        if token.head == verb_token and "subj" in token.dep_:
            subj_token = token
            break
            
    if not subj_token:
        return "3s" # Default if no subject found
    
    text = subj_token.text.lower()
    
    # Pronouns
    if text == "i": return "1s"
    if text == "you": return "2s"
    if text == "we": return "1p"
    if text == "they": return "3p"
    if text in ["he", "she", "it"]: return "3s"
    
    # Nouns
    morph = subj_token.morph.to_dict()
    number = morph.get("Number", "Sing")
    
    if number == "Plur":
        return "3p"
    else:
        return "3s"

def analyze_automatically(clause, data):
    """
    Uses spaCy to analyze the clause structure and morphology.
    Returns: (Success, Conjugated_Verb, Clean_Lemma)
    """
    if not nlp: return False, "", ""
    
    doc = nlp(clause)
    verb_token = None
    
    # 1. Search for ROOT Verb/Aux
    for token in doc:
        if token.dep_ == "ROOT" and token.pos_ in ["VERB", "AUX"]:
            verb_token = token
            break
            
    # 2. Search for any Verb
    if not verb_token:
        for token in doc:
            if token.pos_ in ["VERB", "AUX"]:
                verb_token = token
                break
                
    # 3. Aggressive fallback for single words (e.g., "Ran")
    if not verb_token and len(doc) <= 2:
        for token in doc:
             if token.pos_ not in ["DET", "PRON"]:
                 verb_token = token
                 break
                 
    if not verb_token: return False, "", ""
    
    # Get Lemma and Forms
    lemma = verb_token.lemma_.lower()
    
    ger, pp = generate_english_forms(lemma)
    
    if not ger or not pp: return False, "", ""
    
    data.infinitive = lemma
    data.gerund = ger
    data.participle = pp
    
    # Detect Person/Number
    data.person_number = detect_person_number(doc, verb_token, verb_token.i)
    
    # Split Sentence
    idx = verb_token.i
    data.subject = doc[:idx].text.strip()
    data.postverbal = doc[idx+1:].text.strip()
    
    return True, verb_token.text, lemma


def collect_clause_info(clause: str, data: ClauseData) -> ClauseData:
        
    success, verb_visual, lemma_visual = analyze_automatically(clause, data)
    
    if success:
        # Map for user-friendly display
        pn_map = {
            "1s": "1st person singular (I)",
            "2s": "2nd person (You)",
            "3s": "3rd person singular (He/She/It)",
            "1p": "1st person plural (We)",
            "2p": "2nd person plural (You)", 
            "3p": "3rd person plural (They)"
        }
        desc_pn = pn_map.get(data.person_number, "Unknown")
        
        print("\nThis is an analysis of some of the morphological and structural features of this clause:")
        print("\n" + "="*50)
        print(f"• Verb:             «{verb_visual}»")
        print(f"• Person/Number:    {desc_pn}")
        print("-" * 50)
        print(f"• Infinitive:       {lemma_visual}")
        print(f"• Gerund:           {data.gerund}")
        print(f"• Past Participle:  {data.participle}")
        print("-" * 50)
        print(f"• Before verb:      «{data.subject if data.subject else 'Ø'}»")
        print(f"• After verb:       «{data.postverbal if data.postverbal else 'Ø'}»")
        print("="*50)
        
        if yes_no("\nIs this analysis correct? (y/n): "):
            data.got_forms = True
            return data
        else:
            print("\nUnderstood. Switching to manual entry.")

    # --- MANUAL FALLBACK ---
    data.gerund = prompt_user(f"\nType the GERUND of the verb in '{clause}' (e.g., 'melting', 'telling'): ")
    data.participle = prompt_user(f"Type the PAST PARTICIPLE (e.g., 'melted', 'told'): ")
    
    subj_in = prompt_user(f"Type everything that comes BEFORE the verb in '{clause}' (0 if nothing): ")
    data.subject = "" if subj_in == "0" else subj_in
    
    post_in = prompt_user(f"Type everything that comes AFTER the verb in '{clause}' (0 if nothing): ")
    data.postverbal = "" if post_in == "0" else post_in
    
    pn_question = "Type the person and number of the verb"
    pn_suffix = "(1s/2s/3s/1p/2p/3p): "
    pn_options: List[str] = ['1s', '2s', '3s', '1p', '2p', '3p']
    data.person_number = multiple_choice(pn_question, pn_options, pn_suffix)
    
    data.got_forms = True
    return data


def build_prog(past: bool, data: ClauseData) -> str:
    be = BE_PAST[data.person_number] if past else BE_PRESENT[data.person_number]
    parts = [data.subject, f"{be} {data.gerund}", data.postverbal]
    return " ".join(p for p in parts if p)


def build_perfect(data: ClauseData) -> str:
    have = HAVE_PRESENT[data.person_number]
    parts = [data.subject, f"{have} {data.participle}", data.postverbal]
    return " ".join(p for p in parts if p)


def build_stop(data: ClauseData) -> str:
    parts = [data.subject or "(subject)", f"stopped {data.gerund}", data.postverbal]
    return " ".join(p for p in parts if p)


# ------------------------- Diagnostics -------------------------

def causativity_test(clause: str) -> bool:
    print("\nCAUSATIVITY TEST")
    print(f"\nTry to paraphrase '{clause}' following these models: ")
    print("• The cat broke the vase → The cat CAUSED the vase to break")
    print("• Ana gave Pepe a book → Ana CAUSED Pepe to have a book")
    paraphrase = prompt_user("\nType your paraphrase (or '0' if not possible): ")
    if paraphrase == '0' or not paraphrase.strip():
        return False
    print("\nConsider the following:")
    cap = paraphrase[0].upper() + paraphrase[1:]
    print(f"• '{cap}' should preserve the meaning of '{clause}'.")
    print(f"• '{cap}' must not add new arguments nor duplicate existing ones in '{clause}'.")
    print("• Exclude consumption ('eat an apple') and creation ('write a story') readings.")
    return yes_no(f"\nDoes '{cap}' meet these criteria? (y/n): ")


def get_basic_event() -> str:
    while True:
        ev = prompt_user("\nType the resulting event/state without the cause (e.g., 'the vase broke', 'Pepe has a book').\nIf none comes to mind, type '0': ")
        if ev == "0" or ev.strip():
            return ev
        print("\nPlease enter a valid clause or '0'.")


def stativity_test(clause: str) -> bool:
    print("\nSTATIVITY TEST")
    return not yes_no(
        f"\nConsider the following dialogue:"
        f"\n— What happened a moment ago / yesterday / last month?"
        f"\n— {clause[0].upper() + clause[1:]}."
        f"\n\nDo you think '{clause}' is a good answer to that question (for at least one time option)? (y/n): ")


def dynamicity_test(data: ClauseData) -> bool:
    prog = build_prog(False, data)
    print("\nDYNAMICITY TEST")
    return yes_no(
        f"\nConsider: '{prog[0].upper() + prog[1:]} vigorously / forcefully / with effort'."
        f"\nIs this acceptable with at least one of the options? (y/n): ")


def punctuality_test(data: ClauseData) -> bool:
    prog_past = build_prog(True, data)
    print("\nPUNCTUALITY TEST")
    return yes_no(
        f"\nConsider: '{prog_past[0].upper() + prog_past[1:]} for an hour / for a month'."
        f"\nIs this expression acceptable (with at least one option) WITHOUT forcing an iterative or imminent reading? (y/n): ")


def telicity_test(data: ClauseData) -> bool:
    prog = build_prog(False, data)
    stop_expr = build_stop(data)
    perfect = build_perfect(data)
    print("\nTELICITY TEST")
    q = (f"\nImagine that {prog} and suddenly {stop_expr}."
         f"\nWould it then be true to say: '{perfect}'? (y/n): ")
    return not yes_no(q)


# ------------------------- Classification -------------------------

def determine_subtype(feats: Features) -> Optional[str]:
    if feats.stative:
        return "STATE"
    elif feats.punctual and feats.telic:
        return "ACHIEVEMENT"
    elif feats.punctual and not feats.telic:
        return "SEMELFACTIVE"
    elif not feats.punctual and feats.telic and feats.dynamic:
        return "ACTIVE_ACCOMPLISHMENT"
    elif not feats.punctual and not feats.telic and feats.dynamic:
        return "ACTIVITY"
    elif not feats.punctual and feats.telic and not feats.dynamic:
        return "ACCOMPLISHMENT"
    elif not feats.punctual and not feats.telic and not feats.dynamic:
        return "PROCESS"
    else:
        return None


def determine_aktionsart(feats: Features) -> Optional[Aktionsart]:
    sub = determine_subtype(feats)
    if sub is None:
        return None
    if feats.causative:
        return Aktionsart[f"CAUSATIVE_{sub}"]
    else:
        return Aktionsart[sub]


def verify_adjuncts_cleanup(clause: str) -> str:
    """
    Asks the user to verify if the clause is free of adjuncts
    that might interfere with the tests.
    """
    print(f"\nThis is the clause we will test: \n{BOLD}'{clause}{RESET}'")
    print("For the tests to work correctly, the clause must be 'clean'.")
    print("\nEnsure it does NOT contain:")
    print("• Time expressions (e.g., 'yesterday', 'always', 'never', 'on Monday')")
    print("• Manner expressions (e.g., 'quickly', 'well', 'with calm')")
    print("• Negation (e.g., 'not', 'never')")
    
    if yes_no("\nDoes your clause contain any of these elements? (y/n): "):
        clean_clause = prompt_user(f"\nPlease type '{clause}' again WITHOUT those elements (e.g., 'Peter ran' instead of 'Peter never ran yesterday'): ")
        while not clean_clause.strip():
            clean_clause = prompt_user("You didn't type anything. Try again: ")
        return clean_clause
    return clause

# ------------------------- Orchestration -------------------------

def obtain_features(clause: str, data: ClauseData) -> Union[Features, None]:
    feats = Features()
    data.got_forms = False

    caused = causativity_test(clause)
    if caused:
        basic_event = get_basic_event()
        if basic_event == "0":
            feats.causative = False
            print(f"\n{BOLD}Predicate is [-causative]{RESET}")
        else:
            feats.causative = True
            print(f"\n{BOLD}Predicate is [+causative]{RESET}")
            clause = basic_event
    else:
        feats.causative = False
        print(f"\n{BOLD}Predicate is [-causative]{RESET}")

    time.sleep(0.5)
    clause = verify_adjuncts_cleanup(clause)

    time.sleep(0.5)
    collect_clause_info(clause, data)

    time.sleep(0.5)
    feats.stative = stativity_test(clause)
    print(f"\n{BOLD}Predicate is [{'+' if feats.stative else '-'}stative]{RESET}")
    time.sleep(0.5)

    if not feats.stative:
        feats.punctual = not punctuality_test(data)
        print(f"\n{BOLD}Predicate is [{'+' if feats.punctual else '-'}punctual]{RESET}")
        time.sleep(0.5)

        feats.telic = telicity_test(data)
        print(f"\n{BOLD}Predicate is [{'+' if feats.telic else '-'}telic]{RESET}")
        time.sleep(0.5)

        feats.dynamic = dynamicity_test(data)
        print(f"\n{BOLD}Predicate is [{'+' if feats.dynamic else '-'}dynamic]{RESET}")
        time.sleep(0.5)

    return feats


def show_result(original_clause: str, akt: Aktionsart, feats: Features) -> None:
    print("\nRESULT")
    print(f"\n{BOLD}The aktionsart of the predicate in '{original_clause}' is {akt.value.upper()}.{RESET}")

    is_state = akt in [Aktionsart.STATE, Aktionsart.CAUSATIVE_STATE]

    feat_str = [
        f"[{'+' if feats.causative else '-'}causative]",
        f"[{'+' if feats.stative else '-'}stative]",
        f"[{'+' if (not is_state and feats.punctual) else '-'}punctual]",
        f"[{'+' if (not is_state and feats.telic) else '-'}telic]",
    ]

    if is_state:
        feat_str.append("[-dynamic]")
        is_dyn = False
    else:
        feat_str.append(f"[{'+' if feats.dynamic else '-'}dynamic]")
        is_dyn = feats.dynamic

    print("\nThis predicate is classified as such because it shows the following features:")
    print(' '.join(feat_str))


def run_ls(akt: Aktionsart, original_clause: str, is_dynamic: bool) -> None:
    """
    Call the logical structure module (ls_en.py).
    """
    try:
        dyn_str = "dynamic" if is_dynamic else "non_dynamic"
        cmd = [sys.executable, "-u", LS_SCRIPT, akt.value, original_clause, dyn_str]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running {LS_SCRIPT}: {e}")
    except FileNotFoundError:
        print(f"File {LS_SCRIPT} not found in the current directory.")


def main() -> None:
    set_english_locale()
    clear_console()
    print("\nThis program will help you identify the aktionsart of the main predicate in a clause.")
    print("\n(Type «...» at any time to restart the analysis).")

    while True:
        try:
            original = prompt_user(
                "\nPlease type a clause with the verb you want to test"
                "\nconjugated in the SIMPLE PAST (e.g., 'Peter ran home')."
                "\nIf it sounds very odd, type it in PRESENT (e.g., 'Mary knows English')."
                "\n\nClause: "
            )

            if not original:
                print("\nYou did not type any clause.")
                continue

            clause = original
            data = ClauseData()

            feats = obtain_features(clause, data)
            if feats is None:
                continue
            akt = determine_aktionsart(feats)
            if akt is None:
                restart_message()
                continue
            show_result(original, akt, feats)

            if not yes_no("\nDo you want to identify the aktionsart of another predicate? (y/n): "):
                print("\nReturning to main menu...")
                time.sleep(1)
                try:
                    subprocess.run([sys.executable, "main.py"], check=True)
                except FileNotFoundError:
                    print("Error: main.py not found in the current directory.")
                except subprocess.CalledProcessError as e:
                    print(f"Error running main.py: {e}")
                return
            else:
                time.sleep(0.5)
                clear_console()

        except RestartAnalysis:
            print("\n" + "-" * 30)
            print("Analysis restarted.")
            print("-" * 30)
            time.sleep(0.8)
            clear_console()
            continue

        except Exception as e:
            logging.error(f"\nUnexpected error: {e}")
            print("\nAn error occurred. Please, try again.")


if __name__ == "__main__":
    main()