from dataclasses import dataclass


def normalize(text: str) -> str:
    return " ".join(text.casefold().replace("ё", "е").split())


def phrases(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(normalize(p) for p in value.split(";") if p.strip()))


@dataclass(frozen=True)
class Rule:
    any_of: tuple[str, ...] = ()
    all_of: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()

    @classmethod
    def parse(cls, any_of="", all_of="", exclude=""):
        return cls(phrases(any_of), phrases(all_of), phrases(exclude))

    def matches(self, text: str) -> bool:
        text = normalize(text)
        return bool(text) and (
            not self.any_of or any(p in text for p in self.any_of)
        ) and all(p in text for p in self.all_of) and not any(p in text for p in self.exclude)


def message_link(chat_id: int, message_id: int, username: str | None = None) -> str:
    if username:
        return f"https://t.me/{username}/{message_id}"
    if str(chat_id).startswith("-100"):
        return f"https://t.me/c/{str(chat_id)[4:]}/{message_id}"
    return ""
