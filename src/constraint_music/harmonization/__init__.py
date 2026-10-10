"""Request-bound SATB harmonization with a separate, explicit contract.

The legacy composition API retains its stricter musical policy. This API solves
complete chords under the obligations in HarmonizationRequest, without hidden
root-doubling, outer-voice seventh or melodic-style restrictions.
"""

from .models import ChordRequest, HarmonizationRequest, HarmonizationResult
from .verifier import verify_harmonization

__all__ = [
    "ChordRequest",
    "HarmonizationRequest",
    "HarmonizationResult",
    "verify_harmonization",
]
