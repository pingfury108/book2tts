from django.db import migrations


def migrate_voice_settings(apps, schema_editor):
    DialogueScript = apps.get_model('workbench', 'DialogueScript')
    DialogueSegment = apps.get_model('workbench', 'DialogueSegment')
    VoiceRole = apps.get_model('workbench', 'VoiceRole')

    scripts = DialogueScript.objects.all().iterator()
    for script in scripts:
        data = script.script_data or {}

        # 确保脚本数据为字典
        if not isinstance(data, dict):
            continue

        voice_settings = data.get('voice_settings')
        if not isinstance(voice_settings, dict):
            voice_settings = {}

        segments = (
            DialogueSegment.objects
            .filter(script=script)
            .select_related('voice_role')
            .order_by('sequence')
        )

        updated = False
        for segment in segments:
            if not segment.voice_role_id:
                continue

            voice_role = segment.voice_role
            if not voice_role:
                continue

            if voice_settings.get(segment.speaker):
                continue

            voice_settings[segment.speaker] = {
                'provider': voice_role.tts_provider,
                'voice_name': voice_role.voice_name,
            }
            updated = True

        if updated:
            data['voice_settings'] = voice_settings
            DialogueScript.objects.filter(pk=script.pk).update(script_data=data)


def noop(apps, schema_editor):
    """Reverse migration intentionally left blank."""


class Migration(migrations.Migration):

    dependencies = [
        ('workbench', '0021_ttsproviderconfig'),
    ]

    operations = [
        migrations.RunPython(migrate_voice_settings, noop),
        migrations.RemoveField(
            model_name='dialoguesegment',
            name='voice_role',
        ),
        migrations.DeleteModel(
            name='VoiceRole',
        ),
    ]

