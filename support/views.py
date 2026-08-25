from rest_framework import viewsets, mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
from .models import SupportTicket
from .serializers import SupportTicketSerializer

MAX_OPEN_TICKETS_PER_USER = 10


class SupportViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = [IsAuthenticated]
    serializer_class = SupportTicketSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'user'

    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        open_count = SupportTicket.objects.filter(
            user=request.user,
            status__in=['open', 'in_progress']
        ).count()

        if open_count >= MAX_OPEN_TICKETS_PER_USER:
            return Response(
                {"detail": f"You already have {open_count} open tickets. "
                           f"Please wait for existing tickets to be resolved before submitting new ones."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)