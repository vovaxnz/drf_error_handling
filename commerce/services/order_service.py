from django.db import transaction
from commerce.models.orders import Order, OrderItem
from commerce.models.quotes import Quote
from commerce.statuses import QuoteStatus
from common.exceptions import DomainError


class OrderService:

    @staticmethod
    @transaction.atomic
    def create_from_quote(*, quote: Quote, client, idempotency_key: str) -> Order:

        quote = Quote.objects.select_for_update().get(pk=quote.pk)

        if quote.status != QuoteStatus.ACCEPTED:
            raise DomainError(
                message="Cannot create order from quote {0} with status {1}. Expected accepted.".format(
                    quote.id, quote.status
                ),
                code="invalid_quote_status",
                http_status=400,
            )

        if not quote.items.exists():
            raise DomainError(
                message="Cannot create order from quote {0} because it has no items.".format(
                    quote.id
                ),
                code="empty_quote",
                http_status=400,
            )

        order = Order.objects.create(
            client=client,
            quote=quote,
            currency=quote.currency,
            total_amount=quote.get_total_price(),
            idempotency_key=idempotency_key,
        )

        items = [
            OrderItem(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.unit_price,
                currency=item.currency,
                product_title=item.product.title,
                sku=item.product.sku,
                product_url=item.product.product_url,
            )
            for item in quote.items.all()
        ]

        OrderItem.objects.bulk_create(items)

        return order