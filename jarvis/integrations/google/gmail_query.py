"""
Gmail query builder — helpers para construção de queries Gmail API.
"""

from __future__ import annotations

_CAT_MAP: dict[str, str] = {
    # primary
    "primary":    "primary",
    "principal":  "primary",
    "importantes": "primary",
    # promotions
    "promotions":  "promotions",
    "promotion":   "promotions",
    "promoções":   "promotions",
    "promocoes":   "promotions",
    "promoçoes":   "promotions",
    "promoção":    "promotions",
    "promocao":    "promotions",
    # social
    "social":  "social",
    # updates
    "updates":       "updates",
    "update":        "updates",
    "atualizações":  "updates",
    "atualizacoes":  "updates",
    "atualização":   "updates",
    "atualizacao":   "updates",
    "notificações":  "updates",
    "notificacoes":  "updates",
    # forums
    "forums":  "forums",
    "forum":   "forums",
    "fóruns":  "forums",
    "foruns":  "forums",
    "fórum":   "forums",
}

_VALID = ("primary", "promotions", "social", "updates", "forums")

CATEGORY_ERROR = (
    "Categoria inválida: '{value}'. "
    "Use: primary, promotions, social, updates, forums "
    "(ou: principal, promoções, social, atualizações, fóruns)."
)


def normalize_category(cat: str | None) -> tuple[str | None, str | None]:
    """
    Normaliza a categoria recebida do usuário.
    Retorna (categoria_normalizada, mensagem_de_erro).
    - Se cat é None/vazio → (None, None) — sem filtro, comportamento padrão.
    - Se inválido → (None, CATEGORY_ERROR formatado).
    - Se válido → (categoria, None).
    """
    if not cat:
        return None, None
    normalized = _CAT_MAP.get(cat.strip().lower())
    if normalized is None:
        return None, CATEGORY_ERROR.format(value=cat.strip())
    return normalized, None


def build_query(
    base: str,
    user_query: str | None,
    category: str | None,
    inbox_only: bool = True,
) -> str:
    """
    Constrói a query final para Gmail API.

    Args:
        base:       termos base (ex: "newer_than:1d", "is:unread")
        user_query: query livre do usuário (ex: "from:alguem")
        category:   categoria já normalizada (ex: "primary", "promotions")
        inbox_only: se True, adiciona "in:inbox" ao início

    Retorna string pronta para uso como q= na Gmail API.
    """
    parts: list[str] = []

    if inbox_only:
        parts.append("in:inbox")

    if base:
        parts.append(base)

    if category:
        parts.append(f"category:{category}")

    if user_query:
        parts.append(f"({user_query})" if parts else user_query)

    return " ".join(parts)
