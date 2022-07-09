from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post, User


@cache_page(20)
def index(request):
    template = "posts/index.html"
    posts = Post.objects.select_related("group").all()
    paginator = Paginator(posts, settings.PER_PAGE_COUNT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "page_obj": page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    template = "posts/group_list.html"
    group = get_object_or_404(Group, slug=slug)
    posts = group.post_set.all()
    paginator = Paginator(posts, settings.PER_PAGE_COUNT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "group": group,
        "posts": posts,
        "page_obj": page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    template = "posts/profile.html"
    user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author__exact=user)
    posts_count = Post.objects.filter(author__exact=user).count
    paginator = Paginator(posts, settings.PER_PAGE_COUNT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    if request.user.is_authenticated:
        following = Follow.objects.filter(
            user__exact=request.user, author__exact=user
        ).exists()
        if request.user != user.username:
            non_author = True
        else:
            non_author = False
    else:
        following = False
        non_author = False

    context = {
        "author": user,
        "posts_count": posts_count,
        "page_obj": page_obj,
        "following": following,
        "non_author": non_author,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    posts_count = Post.objects.filter(author__exact=post.author).count
    template = "posts/post_detail.html"
    comments = Comment.objects.filter(post_id__exact=post.pk)
    context = {
        "posts_count": posts_count,
        "post": post,
        "form": CommentForm(),
        "comments": comments,
    }
    return render(request, template, context)


@login_required
def post_create(request):
    if request.method == "POST":
        form = PostForm(
            request.POST or None,
            files=request.FILES or None,
        )
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect("posts:profile", username=request.user.username)
        context = {
            "form": form,
        }
        return render(request, "posts/create_post.html", context)
    form = PostForm()
    context = {
        "form": form,
    }
    return render(request, "posts/create_post.html", context)


@login_required
def post_edit(request, post_id):
    is_edit = True
    post = get_object_or_404(Post, pk=post_id)
    author = post.author
    if request.user != author:
        return redirect("posts:post_detail", post_id=post.pk)
    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
    if form.is_valid() and request.method == "POST":
        form.save()
        return redirect("posts:post_detail", post_id)
    context = {
        "form": form,
        "is_edit": is_edit,
        "post": post,
    }
    return render(request, "posts/create_post.html", context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect("posts:post_detail", post_id=post_id)


@login_required
def follow_index(request):
    follower_user = request.user
    following_authors = Follow.objects.filter(user=follower_user).values("author")
    posts = Post.objects.filter(author__in=following_authors)
    template = "posts/follow.html"
    paginator = Paginator(posts, settings.PER_PAGE_COUNT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "page_obj": page_obj,
        "following_authors": following_authors,
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    following_user = request.user
    if author != following_user:
        if Follow.objects.get_or_create(user=following_user, author=author):
            return redirect("posts:profile", username=username)
    else:
        return redirect("posts:posts_index")


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    if Follow.objects.filter(user=user, author=author).exists():
        Follow.objects.filter(user=user, author=author).delete()
        return redirect("posts:profile", username=username)
    else:
        return redirect("posts:profile", username=username)
