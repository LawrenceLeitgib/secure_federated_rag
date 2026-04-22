from datasets import load_dataset
from pathlib import Path
import re

# -----------------------------
# Configuration
# -----------------------------
OUTPUT_DIR = Path("wiki_data_owners")
ARTICLES_PER_OWNER = 10

# 5 subjects = 5 data owners.
#
# These titles are a curated subset of Wikipedia's Vital articles level 3/4 pages.
# Keeping selection title-based avoids the previous problem where broad keyword
# matches picked early alphabetical but low-value pages such as "A" or
# disambiguation pages.
VITAL_ARTICLES_BY_OWNER = {
    "data_owner_1_science": [
        "Algebra",
        "Anatomy",
        "Astronomy",
        "Atom",
        "Biology",
        "Botany",
        "Calculus",
        "Cell (biology)",
        "Chemistry",
        "Ecology",
        "Earth science",
        "Electron",
        "Evolution",
        "Genetics",
        "Geology",
        "Geometry",
        "Mathematics",
        "Medicine",
        "Molecule",
        "Neuroscience",
        "Number theory",
        "Organism",
        "Physics",
        "Probability",
        "Quantum mechanics",
        "Science",
        "Scientific method",
        "Statistics",
        "Zoology",
    ],
    "data_owner_2_history": [
        "American Civil War",
        "Ancient Egypt",
        "Ancient Greece",
        "Ancient Rome",
        "British Empire",
        "Byzantine Empire",
        "Cold War",
        "Crusades",
        "French Revolution",
        "Great Depression",
        "History",
        "Industrial Revolution",
        "Middle Ages",
        "Mongol Empire",
        "Napoleonic Wars",
        "Ottoman Empire",
        "Renaissance",
        "Roman Empire",
        "Russian Revolution",
        "Soviet Union",
        "World War I",
        "World War II",
    ],
    "data_owner_3_technology": [
        "Agriculture",
        "Artificial intelligence",
        "Automobile",
        "Aviation",
        "Biotechnology",
        "Computer",
        "Computer science",
        "Electricity",
        "Engineering",
        "Factory",
        "Industrialisation",
        "Internet",
        "Machine",
        "Mass media",
        "Nuclear power",
        "Printing",
        "Radio",
        "Rail transport",
        "Ship",
        "Steam engine",
        "Technology",
        "Telephone",
        "Transport",
        "Wheel",
        "Writing",
    ],
    "data_owner_4_geography": [
        "Africa",
        "Antarctica",
        "Asia",
        "Atlantic Ocean",
        "Australia",
        "City",
        "Climate",
        "Continent",
        "Country",
        "Desert",
        "Earth",
        "Europe",
        "Geography",
        "Indian Ocean",
        "Island",
        "Lake",
        "Mountain",
        "North America",
        "Ocean",
        "Pacific Ocean",
        "River",
        "South America",
        "Southern Ocean",
    ],
    "data_owner_5_art_culture": [
        "Architecture",
        "Art",
        "Classical music",
        "Cinema",
        "Dance",
        "Drama",
        "Film",
        "Jazz",
        "Literature",
        "Modernism",
        "Music",
        "Novel",
        "Opera",
        "Painting",
        "Poetry",
        "Religion",
        "Sculpture",
        "Theatre",
        "Visual arts",
    ],
}

# Set to None to scan until enough Vital articles are found. A finite limit is
# useful for quick smoke tests, but may miss relevant pages because the dataset
# is ordered alphabetically.
MAX_ARTICLES_TO_SCAN = None
MIN_ARTICLE_CHARS = 2_000
CLEAR_EXISTING_OWNER_FILES = True
REJECT_TITLE_PATTERNS = (
    r"\bdisambiguation\b",
    r"^Index of ",
    r"^List of ",
    r"^Outline of ",
)


# -----------------------------
# Helpers
# -----------------------------
def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_title(title: str) -> str:
    return normalize_text(title).casefold()


def is_quality_article(example) -> bool:
    title = normalize_text(example["title"])
    text = example["text"].strip()

    if len(text) < MIN_ARTICLE_CHARS:
        return False

    return not any(
        re.search(pattern, title, flags=re.IGNORECASE)
        for pattern in REJECT_TITLE_PATTERNS
    )


def save_article(path: Path, example):
    title = normalize_text(example["title"])
    url = normalize_text(example["url"])
    text = example["text"].strip()

    content = f"TITLE: {title}\nURL: {url}\n\n{text}\n"
    path.write_text(content, encoding="utf-8")


def prepare_owner_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

    if not CLEAR_EXISTING_OWNER_FILES:
        return

    for old_file in path.glob("*.txt"):
        old_file.unlink()


# -----------------------------
# Main
# -----------------------------
def main():
    print("Loading Wikipedia dataset...")
    dataset = load_dataset("wikimedia/wikipedia", "20231101.en", split="train")

    if MAX_ARTICLES_TO_SCAN is not None:
        dataset = dataset.select(range(min(MAX_ARTICLES_TO_SCAN, len(dataset))))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for owner_name in VITAL_ARTICLES_BY_OWNER:
        prepare_owner_directory(OUTPUT_DIR / owner_name)

    counts = {owner_name: 0 for owner_name in VITAL_ARTICLES_BY_OWNER}
    used_titles = set()
    title_to_owner = {
        normalize_title(title): owner_name
        for owner_name, titles in VITAL_ARTICLES_BY_OWNER.items()
        for title in titles
    }

    print("Selecting Vital articles...")

    for example in dataset:
        title = normalize_text(example["title"])
        normalized_title = normalize_title(title)

        if normalized_title not in title_to_owner:
            continue

        owner_name = title_to_owner[normalized_title]
        if counts[owner_name] >= ARTICLES_PER_OWNER:
            continue
        if normalized_title in used_titles:
            continue
        if not is_quality_article(example):
            print(f"[{owner_name}] skipped low-quality page: {title}")
            continue

        file_index = counts[owner_name] + 1
        safe_title = re.sub(r'[^a-zA-Z0-9._-]+', "_", title)[:80]
        out_path = OUTPUT_DIR / owner_name / f"{file_index:02d}_{safe_title}.txt"

        save_article(out_path, example)
        counts[owner_name] += 1
        used_titles.add(normalized_title)

        print(f"[{owner_name}] saved: {title}")

        if all(count >= ARTICLES_PER_OWNER for count in counts.values()):
            break

    print("\nDone.")
    for owner_name, count in counts.items():
        print(f"{owner_name}: {count} articles")

    missing = [owner for owner, count in counts.items() if count < ARTICLES_PER_OWNER]
    if missing:
        print("\nWarning: not enough matches found for:")
        for owner in missing:
            print(f" - {owner}")


if __name__ == "__main__":
    main()
