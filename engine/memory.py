from pathlib import Path
import json


# ============================================================
# CONFIG
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

MEMORY_FILE = DATA_DIR / "conversation_memory.json"

MAX_MEMORY_MESSAGES = 10


# ============================================================
# LOAD MEMORY
# ============================================================

def load_memory():
    """Doc lich su conversation."""

    if not MEMORY_FILE.exists():
        return []

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            history = json.load(file)

    except (
        json.JSONDecodeError,
        OSError
    ):

        return []

    if not isinstance(
        history,
        list
    ):

        return []

    return history


# ============================================================
# GET RECENT MEMORY
# ============================================================

def get_recent_memory(
    limit=MAX_MEMORY_MESSAGES
):
    """
    Lay cac message gan nhat
    de dua vao context.
    """

    history = load_memory()

    if not history:
        return []

    return history[-limit:]


# ============================================================
# GET MEMORY TEXT
# ============================================================

def get_memory_text(
    limit=MAX_MEMORY_MESSAGES
):
    """
    Chuyen conversation memory
    thanh text de dua vao LLM.
    """

    history = get_recent_memory(
        limit
    )

    if not history:
        return ""

    conversation = []

    for message in history:

        role = message.get(
            "role",
            ""
        )

        content = message.get(
            "content",
            ""
        )

        if not role or not content:
            continue

        conversation.append(
            f"{role}: {content}"
        )

    return "\n".join(
        conversation
    )


# ============================================================
# GET ACTIVE ENTITIES
# ============================================================

def get_active_entities(
    limit=MAX_MEMORY_MESSAGES
):
    """
    Lay cac entity gan nhat
    trong conversation memory.

    Entity moi nhat duoc uu tien.
    """

    history = get_recent_memory(
        limit
    )

    if not history:
        return []

    active_entities = []

    seen = set()

    # Doc tu message moi nhat -> cu nhat
    for message in reversed(history):

        entities = message.get(
            "entities",
            []
        )

        if not isinstance(
            entities,
            list
        ):

            continue

        for entity in entities:

            if not isinstance(
                entity,
                dict
            ):

                continue

            entity_id = entity.get(
                "entity_id"
            )

            canonical_name = entity.get(
                "canonical_name"
            )

            key = (
                entity_id
                or canonical_name
            )

            if not key:
                continue

            if key in seen:
                continue

            seen.add(
                key
            )

            active_entities.append(
                entity
            )

    return active_entities


# ============================================================
# GET LAST ENTITY
# ============================================================

def get_last_entity():
    """
    Lay entity gan nhat trong conversation.

    Vi du:

    User:
        C# la gi?

    Entity:
        C#

    Return:
        {
            "entity_id": "csharp",
            "canonical_name": "C#",
            ...
        }
    """

    entities = get_active_entities()

    if not entities:
        return None

    return entities[0]


# ============================================================
# SAVE MEMORY
# ============================================================

def save_memory(
    history
):
    """Luu lich su conversation."""

    MEMORY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        MEMORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            history,
            file,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# ADD MESSAGE
# ============================================================

def add_message(
    history,
    role,
    content,
    entities=None
):
    """
    Them message vao conversation memory.

    entities:
        Danh sach entity da duoc
        NER + Entity Resolution xu ly.

    Vi du:

    {
        "entity_id": "csharp",
        "canonical_name": "C#",
        "type": "programming-language"
    }
    """

    if entities is None:
        entities = []

    if not isinstance(
        entities,
        list
    ):
        entities = []

    message = {
        "role": role,
        "content": content,
        "entities": entities
    }

    history.append(
        message
    )

    save_memory(
        history
    )


# ============================================================
# ADD USER MESSAGE
# ============================================================

def add_user_message(
    history,
    content,
    entities=None
):
    """Luu user message kem entity."""

    add_message(
        history,
        "user",
        content,
        entities
    )


# ============================================================
# ADD ASSISTANT MESSAGE
# ============================================================

def add_assistant_message(
    history,
    content,
    entities=None
):
    """Luu assistant message kem entity."""

    add_message(
        history,
        "assistant",
        content,
        entities
    )


# ============================================================
# CLEAR MEMORY
# ============================================================

def clear_memory():
    """Xoa toan bo conversation memory."""

    save_memory([])


# ============================================================
# MODULE STATUS
# ============================================================

if __name__ == "__main__":

    print(
        "Memory is running..."
    )

    history = load_memory()

    print(
        "Messages:",
        len(history)
    )

    entities = get_active_entities()

    print(
        "Active entities:",
        len(entities)
    )