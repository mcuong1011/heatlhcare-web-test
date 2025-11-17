from datetime import timedelta
from django.db import models

from accounts.models import User


class TimeRange(models.Model):
    start = models.TimeField()
    end = models.TimeField()
    is_active = models.BooleanField(default=True)
    slots_per_hour = models.PositiveIntegerField(default=4)

    def get_slot_duration(self):
        """
        Returns slot duration in minutes.
        
        Returns:
            int: Duration in minutes (e.g., 15, 30, 60)
        """
        if self.slots_per_hour is None or self.slots_per_hour <= 0:
            return 30  # Default to 30 minutes if invalid
        
        # Ensure slots_per_hour is reasonable (1-12 slots per hour)
        slots = min(max(int(self.slots_per_hour), 1), 12)

        duration = 60 // slots
    
        # Ensure duration is at least 5 minutes
        return max(5, duration)

    def get_available_slots(self, date):
        """
        Returns list of available time slots for given date.
        
        Args:
            date: datetime.date object
            
        Returns:
            List of time strings in format ['09:00', '09:15', '09:30', ...]
        """
        from datetime import datetime, timedelta
        
        slot_duration = self.get_slot_duration()
        slots = []
        
        # Convert time to datetime for arithmetic operations
        current_dt = datetime.combine(date, self.start)
        end_dt = datetime.combine(date, self.end)
        
        while current_dt < end_dt:
            # Format as HH:MM
            slots.append(current_dt.strftime("%H:%M"))
            # Add duration
            current_dt += timedelta(minutes=slot_duration)
        
        return slots

    class Meta:
        unique_together = ("start", "end")


class Saturday(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    time_range = models.ManyToManyField(TimeRange)


class Sunday(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    time_range = models.ManyToManyField(TimeRange)


class Monday(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    time_range = models.ManyToManyField(TimeRange)


class Tuesday(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    time_range = models.ManyToManyField(TimeRange)


class Wednesday(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    time_range = models.ManyToManyField(TimeRange)


class Thursday(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    time_range = models.ManyToManyField(TimeRange)


class Friday(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    time_range = models.ManyToManyField(TimeRange)
