import re
from rapidfuzz import fuzz
from typing import List, Dict, Any

def normalize_text(text: str) -> str:
    """Helper to strip punctuation and normalize spaces/case."""
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    return " ".join(text.split())

def find_duplicate_names(names_list: List[str], similarity_threshold: int = 85) -> List[Dict[str, Any]]:
    """Identifies near-duplicate groups/clusters within a list of names."""
    unique_names = list(set([n.strip() for n in names_list if isinstance(n, str) and n.strip()]))
    clusters = []
    seen = set()
    
    for idx, name1 in enumerate(unique_names):
        if name1 in seen:
            continue
            
        norm1 = normalize_text(name1)
        variations = []
        max_sim = 0
        
        for name2 in unique_names[idx+1:]:
            if name2 in seen:
                continue
                
            norm2 = normalize_text(name2)
            sim = fuzz.ratio(norm1, norm2)
            
            # Match similarity threshold or substrings
            if sim >= similarity_threshold or (len(norm1) > 3 and len(norm2) > 3 and (norm1 in norm2 or norm2 in norm1)):
                variations.append(name2)
                max_sim = max(max_sim, sim)
                seen.add(name2)
                
        if variations:
            clusters.append({
                "primary": name1,
                "variations": variations,
                "similarity": int(max_sim) if max_sim > 0 else 90,
                "confidence": "High" if max_sim >= 90 else "Medium"
            })
            seen.add(name1)
            
    return clusters
