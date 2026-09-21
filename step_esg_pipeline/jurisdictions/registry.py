from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml


class JurisdictionRegistry:
    """Registry loading and querying configuration for the 13 target jurisdictions."""

    _instance: Optional["JurisdictionRegistry"] = None

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path(__file__).parent
        self.config_dir = Path(config_dir)
        self.jurisdictions: Dict[str, Dict[str, Any]] = {}
        self.domain_to_authority: Dict[str, Dict[str, Any]] = {}
        self._load_all()

    @classmethod
    def get_instance(cls) -> "JurisdictionRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_all(self):
        for yaml_file in self.config_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                if not data or not isinstance(data, dict):
                    continue
                country = data.get("country", "").strip()
                if not country:
                    continue
                self.jurisdictions[country.lower()] = data

                # Index domains
                for auth in data.get("authorities", []):
                    auth_name = auth.get("name", "")
                    tier = auth.get("tier", "TIER_1_PRIMARY_REGULATOR")
                    for d in auth.get("domains", []):
                        clean_d = d.lower().strip()
                        self.domain_to_authority[clean_d] = {
                            "country": country,
                            "authority": auth_name,
                            "tier": tier,
                        }

                for gaz in data.get("official_gazettes", []):
                    gaz_d = gaz.get("domain", "").lower().strip()
                    if gaz_d:
                        self.domain_to_authority[gaz_d] = {
                            "country": country,
                            "authority": gaz.get("name", "Official Gazette"),
                            "tier": "TIER_1_OFFICIAL_LEGISLATION",
                        }
            except Exception:
                pass

    def get_all_countries(self) -> List[str]:
        return [data["country"] for data in self.jurisdictions.values()]

    def get_jurisdiction(self, country: str) -> Optional[Dict[str, Any]]:
        if not country:
            return None
        return self.jurisdictions.get(country.lower().strip())

    def find_authority_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        if not domain:
            return None
        d = domain.lower().strip()
        # Direct lookup
        if d in self.domain_to_authority:
            return self.domain_to_authority[d]
        # Match parent domain (e.g. sub.sec.gov -> sec.gov)
        for reg_domain, auth_info in self.domain_to_authority.items():
            if d == reg_domain or d.endswith("." + reg_domain):
                return auth_info
        return None

    def lookup_domain(self, domain: str, country: str = "") -> Dict[str, Any]:
        if not domain:
            return {"is_official": False, "authority_name": "", "authority_tier": "UNKNOWN", "country": country}
        auth = self.find_authority_by_domain(domain)
        if auth:
            return {
                "is_official": True,
                "authority_name": auth["authority"],
                "authority_tier": auth["tier"],
                "country": auth["country"],
            }
        d = domain.lower().strip()
        if any(gov in d for gov in [".gov.", ".gov/", ".nic.in", ".europa.eu", "legislation.gov.uk", ".gov", "bourse", "exchange"]):
            tier = "TIER_2_EXCHANGE_BODY" if ("bourse" in d or "exchange" in d) else "TIER_1_OFFICIAL_REGULATOR"
            return {
                "is_official": True,
                "authority_name": domain,
                "authority_tier": tier,
                "country": country,
            }
        return {
            "is_official": False,
            "authority_name": domain,
            "authority_tier": "TIER_3_COMMERCIAL_AGGREGATOR",
            "country": country,
        }

    def is_official_domain(self, country: str, domain: str) -> bool:
        auth = self.find_authority_by_domain(domain)
        if not auth:
            return False
        if country and auth["country"].lower() != country.lower():
            # Check if global or EU
            if auth["country"] == "European Union" and country.lower() in ("germany", "france", "eu"):
                return True
            return False
        return True

    def get_authorities(self, country: str) -> List[Dict[str, Any]]:
        j = self.get_jurisdiction(country)
        return j.get("authorities", []) if j else []
