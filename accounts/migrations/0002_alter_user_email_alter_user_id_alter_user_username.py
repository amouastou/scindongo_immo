from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        # IMPORTANT : on ne touche PLUS à l'ID (UUID déjà en base).
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(
                "adresse email",
                max_length=254,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(
                max_length=150,
                blank=True,
                null=True,
                help_text="Nom d'utilisateur interne (optionnel).",
                error_messages={
                    "unique": "Un utilisateur avec ce nom existe déjà.",
                },
            ),
        ),
    ]
