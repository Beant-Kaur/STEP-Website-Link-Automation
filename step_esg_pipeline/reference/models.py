from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RegulatoryAuthority:
    """Represents an authoritative regulatory body from the Authorities sheet."""
    authority_id: str
    country: str
    authority_name: str
    authority_type: str = ""
    official_domain: str = ""
    official_website: str = ""
    trust_level: str = "Official"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authority_id": self.authority_id,
            "country": self.country,
            "authority_name": self.authority_name,
            "authority_type": self.authority_type,
            "official_domain": self.official_domain,
            "official_website": self.official_website,
            "trust_level": self.trust_level,
            "notes": self.notes,
        }


@dataclass
class ResourceVersion:
    """Represents a regulatory amendment, update, or framework version from the Resource_Versions sheet."""
    resource_id: str
    resource_update: str
    issuer: str = ""
    date: str = ""
    relationship: str = ""
    official_url: str = ""
    validator_treatment: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "resource_update": self.resource_update,
            "issuer": self.issuer,
            "date": self.date,
            "relationship": self.relationship,
            "official_url": self.official_url,
            "validator_treatment": self.validator_treatment,
            "notes": self.notes,
        }


@dataclass
class RegulatoryResource:
    """Represents a canonical regulatory source-of-truth from the Resources sheet."""
    resource_id: str
    country: str
    name: str
    issuing_authority: str = ""
    authority_type: str = ""
    regulatory_topic: str = ""
    document_type: str = ""
    official_domain: str = ""
    official_url: str = ""
    publication_date: str = ""
    status_verification_state: str = ""
    lifecycle_notes: str = ""
    related_updated_url: str = ""
    validator_rule: str = ""
    implementation_notes: str = ""
    authority_details: Optional[RegulatoryAuthority] = None
    versions: List[ResourceVersion] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "country": self.country,
            "name": self.name,
            "issuing_authority": self.issuing_authority,
            "authority_type": self.authority_type,
            "regulatory_topic": self.regulatory_topic,
            "document_type": self.document_type,
            "official_domain": self.official_domain,
            "official_url": self.official_url,
            "publication_date": self.publication_date,
            "status_verification_state": self.status_verification_state,
            "lifecycle_notes": self.lifecycle_notes,
            "related_updated_url": self.related_updated_url,
            "validator_rule": self.validator_rule,
            "implementation_notes": self.implementation_notes,
            "authority_details": self.authority_details.to_dict() if self.authority_details else None,
            "versions": [v.to_dict() for v in self.versions],
        }

    def get_related_urls(self) -> List[str]:
        """Returns all recognized official and updated URLs associated with this resource."""
        urls = []
        if self.official_url:
            urls.append(self.official_url)
        if self.related_updated_url and self.related_updated_url not in urls:
            urls.append(self.related_updated_url)
        for v in self.versions:
            if v.official_url and v.official_url not in urls:
                urls.append(v.official_url)
        return urls
