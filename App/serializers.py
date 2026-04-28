from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    employee = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'role', 'employee']

    def get_employee(self, obj):
        if hasattr(obj, 'employee_profile'):
            emp = obj.employee_profile
            return {
                "id": emp.id,
                "name": f"{emp.first_name} {emp.last_name}",
                "branch": emp.branch.name if emp.branch else None
            }
        return None