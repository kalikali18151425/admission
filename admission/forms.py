from django import forms

from .models import HomepageNotice


class HomepageNoticeForm(forms.ModelForm):
    class Meta:
        model = HomepageNotice
        fields = ("title", "message", "link_url", "link_label", "is_active")
        widgets = {
            "message": forms.Textarea(attrs={"rows": 5}),
            "link_url": forms.URLInput(attrs={"placeholder": "https://example.com/notice"}),
            "link_label": forms.TextInput(attrs={"placeholder": "Read details"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("link_url") and not cleaned_data.get("link_label"):
            cleaned_data["link_label"] = "Read details"
        return cleaned_data
