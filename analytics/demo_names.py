"""Deterministic fictional Cambodian-style names for synthetic students."""

from itertools import product
from random import Random


FAMILY_NAMES = (
    "Sok", "Chan", "Lim", "Chea", "Kim", "Noun", "Heng", "Chhim", "Ly", "Keo",
    "Touch", "San", "Ouk", "Yim", "Ros", "Phan", "Chhun", "Khim", "Khoun", "Khin",
    "Sin", "Sou", "Suon", "Mao", "Meas", "Pich", "Pech", "Rin", "Sem", "Som",
    "Srun", "Tep", "Thach", "Ung", "Van", "Yem", "Yi",
)

GIVEN_NAMES = (
    "Dara", "Vannak", "Sreypov", "Ratha", "Sophea", "Sokha", "Sreynich", "Piseth",
    "Sopheak", "Vicheka", "Sreymom", "Rithy", "Chantha", "Sovan", "Sreyleak",
    "Sreyneang", "Borey", "Dalin", "Visal", "Kunthea", "Sreymey", "Sothea", "Sorya",
    "Chanmony", "Sreykim", "Vibol", "Sothy", "Sreyroth", "Sovann", "Phalla",
    "Phanith", "Vuthy", "Kanha", "Pheara", "Rany", "Rachana", "Tola", "Makara",
    "Mony", "Sotheary", "Sambath", "Sreymao", "Sokunthea", "Chantrea", "Serey",
)


def cambodian_student_names(count):
    """Return a stable, varied name sequence; changing score seeds will not rename IDs."""
    if count < 0:
        raise ValueError("Student count cannot be negative")
    rng = Random(2026)
    combinations = [f"{family} {given}" for family, given in product(FAMILY_NAMES, GIVEN_NAMES)]
    names = []
    while len(names) < count:
        rng.shuffle(combinations)
        names.extend(combinations[:count - len(names)])
    return names
