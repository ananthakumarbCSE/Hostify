from django.shortcuts import render,get_object_or_404
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import DiscountCode
from events.models import Event

# Create your views here.


@require_POST
def validate_discount_view(request):
    
    data     = json.loads(request.body)
    event    = get_object_or_404(Event, pk=data.get("event_id"))
    code_str = data.get("code", "").strip().upper()
    subtotal = float(data.get("subtotal", 0))

    try:
        code = DiscountCode.objects.get(event=event, code=code_str)
    except DiscountCode.DoesNotExist:
        return JsonResponse({"valid": False, "message": "Code not found."})

    if not code.is_valid():
        return JsonResponse({"valid": False, "message": "Code is expired or used up."})

    if code.discount_type == "percentage":
        discount_amount = round(subtotal * float(code.value) / 100, 2)
    else:
        discount_amount = min(float(code.value), subtotal)

    return JsonResponse({
        "valid":           True,
        "discount_type":   code.discount_type,
        "value":           float(code.value),
        "discount_amount": discount_amount,
        "message":         f"Code applied! You save ₹{discount_amount}",
    })
