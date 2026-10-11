import json

from django import forms

from .models import MarketRecord, SEGMENT_KEYS


class MarketRecordForm(forms.ModelForm):
    """Add a new year or correct an existing one. Total is worked out from the segments."""

    class Meta:
        model = MarketRecord
        fields = ["year"] + SEGMENT_KEYS
        labels = {"tv": "TV", "movie": "Movies", "video": "Home video", "streaming": "Streaming",
                  "merchandising": "Merchandise", "live_entertainment": "Live events"}

    def clean_year(self):
        year = self.cleaned_data["year"]
        if not 1990 <= year <= 2035:
            raise forms.ValidationError("Enter a year between 1990 and 2035.")
        return year

    def validate_unique(self):
        pass  # an existing year is updated instead of rejected

    def clean(self):
        data = super().clean()
        values = [data.get(k) for k in SEGMENT_KEYS]
        if any(v is not None and v < 0 for v in values):
            raise forms.ValidationError("Values cannot be negative.")
        if data.get("overseas") is None or data.get("merchandising") is None:
            raise forms.ValidationError("Overseas and Merchandise are required.")
        return data

    def save(self, commit=True):
        d = self.cleaned_data
        total = round(sum(d.get(k) or 0 for k in SEGMENT_KEYS), 1)
        obj, _ = MarketRecord.objects.update_or_create(
            year=d["year"],
            defaults={**{k: d.get(k) for k in SEGMENT_KEYS}, "total": total,
                      "record_source": "User entry"})
        return obj


class JsonImportForm(forms.Form):
    """Paste a JSON list of yearly records, e.g. [{"year": 2025, "overseas": 2400, ...}]."""

    payload = forms.CharField(widget=forms.Textarea(attrs={"rows": 7, "spellcheck": "false"}))

    def clean_payload(self):
        try:
            rows = json.loads(self.cleaned_data["payload"])
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"That is not valid JSON: {e.msg} (line {e.lineno}).")
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list) or not rows:
            raise forms.ValidationError("Expected a JSON list of records.")
        cleaned = []
        for r in rows:
            if not isinstance(r, dict) or not isinstance(r.get("year"), int):
                raise forms.ValidationError('Every record needs an integer "year".')
            rec = {"year": r["year"]}
            for k in SEGMENT_KEYS:
                v = r.get(k)
                if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0):
                    raise forms.ValidationError(f'"{k}" for {r["year"]} must be a positive number.')
                rec[k] = v
            if rec["overseas"] is None or rec["merchandising"] is None:
                raise forms.ValidationError(f'{r["year"]}: "overseas" and "merchandising" are required.')
            cleaned.append(rec)
        return cleaned

    def save(self):
        for rec in self.cleaned_data["payload"]:
            year = rec.pop("year")
            total = round(sum(v or 0 for v in rec.values()), 1)
            MarketRecord.objects.update_or_create(
                year=year, defaults={**rec, "total": total, "record_source": "User entry"})
        return len(self.cleaned_data["payload"])
