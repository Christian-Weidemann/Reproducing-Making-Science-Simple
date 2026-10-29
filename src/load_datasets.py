import json
from pathlib import Path

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
        
def load_abstracts_and_summaries(DATA_DIR = Path("../data"), DATASETS = ["elife", "plos"], SPLITS = ["train", "test", "val"]):

    data = {ds:{} for ds in DATASETS}

    for ds in DATASETS:
        abstracts = []
        summaries = []  

        for split in SPLITS:
            for paper in load_json(DATA_DIR / ds / f"{split}.json"):
                abstracts.append(" ".join(paper["abstract"]))
                summaries.append(" ".join(paper["summary"]))

        data[ds]["abstracts"] = abstracts
        data[ds]["summaries"] = summaries

    return data