"""A warning that carries a stable code as well as its sentence.

Every report in capstat ends with ``warnings``: the sentences saying what the
numbers cannot. They are the substance of the library, not decoration -- and
until now they were bare prose. That had two costs, and T-0064 was both of them
at once.

*A caller could not act on one.* The web app can only print a warning, so a
panel that wants to highlight an unstable process has to match on English text.
Rewording a sentence then breaks a consumer silently.

*Nothing could check one.* Warnings were dropped on the Box-Cox path for as long
as that path existed, and no type and no test noticed, because a missing string
looks exactly like a string that was never meant to be there. A set of codes is
comparable; a set of paragraphs is not.

Why a ``str`` subclass rather than a plain dataclass
---------------------------------------------------
So that a warning still *is* its sentence. ``print(w)``, ``"drift" in w``,
``"\\n".join(report.warnings)`` and every one of the ~50 existing assertions
keep working unchanged, which matters more than elegance here: rewriting those
assertions to reach for ``.message`` would have meant touching the tests that
guard the statistics, in the same change that touches the statistics. The code
rides alongside as an attribute, and the HTTP layer serialises both halves.

The equality that comes with that is by message, so two caveats with the same
sentence deduplicate -- which is what the Box-Cox merge in
:func:`~capstat_core.nonnormal.box_cox_capability` relies on.
"""

from __future__ import annotations

__all__ = ["Caveat"]


class Caveat(str):
    """One warning: a stable code, and the prose a person reads.

    ``code`` is namespaced by subject and stable across rewordings --
    ``capability.unstable-process`` stays that whatever the sentence grows into.
    It is the half a program should branch on. The string itself is the half a
    person should read, and the only half that should ever be displayed.
    """

    __slots__ = ("code",)

    code: str

    def __new__(cls, code: str, message: str) -> Caveat:
        if not code:
            raise ValueError(
                "a caveat needs a code; an uncoded warning cannot be acted on"
            )
        caveat = str.__new__(cls, message)
        caveat.code = code
        return caveat

    @property
    def message(self) -> str:
        """The prose alone, as a plain ``str``.

        Present so that a serialiser reading by attribute finds both halves
        under names of their own, rather than one of them being the object.
        """
        return str(self)

    def __repr__(self) -> str:
        return f"Caveat({self.code!r}, {str(self)!r})"
