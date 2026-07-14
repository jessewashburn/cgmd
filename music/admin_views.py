"""
Admin-only views for maintenance operations.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Composer
from .permissions import IsCognitoAdmin
from .utils import is_living_composer


@api_view(['POST'])
@permission_classes([IsCognitoAdmin])
def update_all_is_living(request):
    """
    Update is_living field for all composers based on birth/death years.
    Admin-only endpoint.
    
    POST /api/admin/update-is-living/
    """
    composers = Composer.objects.all()
    updated_count = 0
    updates = []
    
    for composer in composers:
        calculated_living = is_living_composer(composer.birth_year, composer.death_year)
        
        if composer.is_living != calculated_living:
            composer.is_living = calculated_living
            composer.save(update_fields=['is_living'])
            updated_count += 1
            
            updates.append({
                'id': composer.id,
                'name': composer.full_name,
                'birth_year': composer.birth_year,
                'death_year': composer.death_year,
                'is_living': calculated_living
            })
    
    return Response({
        'message': f'Successfully updated {updated_count} composers',
        'updated_count': updated_count,
        'updates': updates[:10]  # Return first 10 for preview
    })
