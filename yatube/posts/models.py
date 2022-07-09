from django.contrib.auth import get_user_model
from django.db import models
from posts.validators import validate_not_empty

User = get_user_model()


class Group(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField(
        validators=[validate_not_empty], verbose_name="Текст поста", help_text=""
    )
    pub_date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        User, related_name="posts", on_delete=models.SET_NULL, null=True
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name="Группа",
        help_text="",
    )
    image = models.ImageField("Картинка", upload_to="posts/", blank=True)

    class Meta:
        ordering = ["-pub_date"]

    def __str__(self):
        return self.text[:15]


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        related_name="comments",
        on_delete=models.SET_NULL,
        null=True,
        help_text="",
    )
    author = models.ForeignKey(
        User, related_name="comments", on_delete=models.CASCADE, null=True
    )
    text = models.TextField(
        validators=[validate_not_empty], verbose_name="Текст комментария", help_text=""
    )
    created = models.DateTimeField(auto_now_add=True)


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        related_name="follower",
        on_delete=models.CASCADE,
        null=True,
    )
    author = models.ForeignKey(
        User, related_name="following", on_delete=models.CASCADE, null=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "author"], name="unique_following")
        ]
