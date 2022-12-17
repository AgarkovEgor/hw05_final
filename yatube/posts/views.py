from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.core.paginator import Paginator
from .models import Post, Group, User, Follow
from .forms import PostForm, CommentForm


def paginator_func(post_list, request):
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    return paginator.get_page(page_number)


@cache_page(20, key_prefix="index_page")
def index(request):
    template = "posts/index.html"
    post_list = Post.objects.all()
    context = {"page_obj": paginator_func(post_list, request=request), "index": True}
    return render(request, template, context)


def group_posts(request, slug):
    template = "posts/group_list.html"
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    context = {
        "group": group,
        "page_obj": paginator_func(post_list=posts, request=request),
    }
    return render(request, template, context)


def profile(request, username):
    template_name = "posts/profile.html"
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    user = request.user
    following = (
        user.is_authenticated
        and Follow.objects.filter(user=user, author=author).exists()
    )
    context = {
        "author": author,
        "following": following,
        "page_obj": paginator_func(post_list=posts, request=request),
    }
    return render(request, template_name, context)


def post_detail(request, post_id):
    template_name = "posts/post_detail.html"
    form = CommentForm()
    post = get_object_or_404(Post, pk=post_id)
    comments = post.comments.all()
    context = {"post": post, "form": form, "comments": comments}
    return render(request, template_name, context)


@login_required
def post_create(request):
    template_name = "posts/post_create.html"
    form = PostForm(request.POST or None, files=request.FILES or None)
    if request.method == "POST" and form.is_valid():
        new_post = form.save(commit=False)
        new_post.author = request.user
        new_post.save()
        return redirect("posts:profile", new_post.author)
    contex = {"form": form}
    return render(request, template_name, contex)


@login_required
def post_edit(request, post_id):
    template_name = "posts/post_create.html"
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect("posts:post_detail", post.id)
    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect("posts:post_detail", post.id)
    context = {"form": form, "is_edit": True}
    return render(request, template_name, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    # Получите пост и сохраните его в переменную post.
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect("posts:post_detail", post_id=post_id)


@login_required
def follow_index(request):
    template = "posts/follow.html"
    post_list = Post.objects.filter(
        author__following__user=request.user,
    ).all()
    context = {"page_obj": paginator_func(post_list, request=request), "follow": True}
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    if author != user:
        Follow.objects.get_or_create(user=user, author=author)
    return redirect("posts:profile", username=username)


@login_required
def profile_unfollow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    if author != user:
        Follow.objects.filter(user=user, author=author).delete()
    return redirect("posts:profile", username=username)
