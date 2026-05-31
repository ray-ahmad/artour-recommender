from dataclasses import dataclass
import logging
from typing import Any

import httpx
import pandas as pd

from app.configs.settings import Settings, get_settings


@dataclass(frozen=True)
class DataBundle:
    places: pd.DataFrame
    interactions: pd.DataFrame


class ArtourRepository:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = logging.getLogger("uvicorn.error")

    async def _request_json(self, client: httpx.AsyncClient, url: str, params: dict[str, str] | None = None) -> Any:
        headers = {}
        if getattr(self.settings, "refresh_trigger_token", None):
            headers["X-ARTOUR-REFRESH-TRIGGER-TOKEN"] = self.settings.refresh_trigger_token
        self.logger.info("Fetching backend data: url=%s params=%s", url, params)
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        self.logger.info("Backend fetch succeeded: url=%s status=%s", url, response.status_code)
        return response.json()

    @staticmethod
    def _extract_records(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("data", "results", "items", "payload"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
            if payload:
                return [payload]
        raise ValueError("Expected JSON list payload or an object containing a list.")

    @staticmethod
    def _normalize_places_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if df.empty:
            return df

        if "placeId" not in df.columns and "id" in df.columns:
            df["placeId"] = df["id"]

        if "placeName" not in df.columns and "name" in df.columns:
            df["placeName"] = df["name"]

        if "placeCategoryName" not in df.columns and "category" in df.columns:
            df["placeCategoryName"] = df["category"].apply(
                lambda value: value.get("name", "") if isinstance(value, dict) else ""
            )

        if "placeDescription" not in df.columns and "description" in df.columns:
            df["placeDescription"] = df["description"]

        if "placeAddress" not in df.columns and "address" in df.columns:
            df["placeAddress"] = df["address"]

        if "placeHashtags" not in df.columns and "hashtags" in df.columns:
            df["placeHashtags"] = df["hashtags"]

        for column in (
            "placeId",
            "placeName",
            "placeCategoryName",
            "placeDescription",
            "placeAddress",
            "placeHashtags",
        ):
            if column in df.columns:
                df[column] = df[column].fillna("").astype(str)

        for column in ("placePrice", "placeRating"):
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

        return df

    @staticmethod
    def _normalize_interactions_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if df.empty:
            return df

        for column in ("userId", "refId", "refModule", "type"):
            if column in df.columns:
                df[column] = df[column].fillna("").astype(str)

        if "value" in df.columns:
            df["value"] = pd.to_numeric(df["value"], errors="coerce").fillna(0)

        if "createdAt" in df.columns:
            df["createdAt"] = pd.to_datetime(df["createdAt"], errors="coerce")

        return df

    def build_bundle_from_payloads(self, places_payload: Any, interactions_payload: Any) -> DataBundle:
        places_records = self._extract_records(places_payload)
        interactions_records = self._extract_records(interactions_payload)
        places_df = self._normalize_places_dataframe(pd.DataFrame(places_records))
        interactions_df = self._normalize_interactions_dataframe(pd.DataFrame(interactions_records))
        return DataBundle(places=places_df, interactions=interactions_df)

    async def refresh(self) -> DataBundle:
        timeout = httpx.Timeout(self.settings.request_timeout_seconds)
        self.logger.info(
            "Repository refresh started: placesUrl=%s interactionsUrl=%s",
            self.settings.backend_places_url,
            self.settings.backend_interactions_url,
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            places_payload = await self._request_json(client, self.settings.backend_places_url)
            interactions_payload = await self._request_json(client, self.settings.backend_interactions_url)
        bundle = self.build_bundle_from_payloads(places_payload, interactions_payload)
        self.logger.info(
            "Repository refresh finished: places=%s interactions=%s",
            int(bundle.places.shape[0]),
            int(bundle.interactions.shape[0]),
        )
        return bundle
