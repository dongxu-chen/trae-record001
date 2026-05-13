import numpy as np

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from .predict import predict


def plot_gp_uncertainty(
    gp,
    X_test,
    X_train=None,
    y_train=None,
    n_std=2.0,
    ax=None,
    figsize=(10, 6),
    show_inducing=True,
    show_samples=False,
    n_samples=5,
    true_func=None,
    color_mean='C0',
    color_fill='C0',
    alpha_fill=0.2,
    labels=None,
    title=None,
    xlabel=None,
    ylabel=None,
    legend=True,
    **kwargs
):
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib is required for plotting. Install it with 'pip install matplotlib'")

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    X_test = np.asarray(X_test)
    if X_test.ndim == 1:
        X_test = X_test.reshape(-1, 1)

    X_test_1d = X_test.ravel() if X_test.shape[1] == 1 else None

    mu, std = predict(gp, X_test, return_std=True, return_cov=False)

    lower = mu - n_std * std
    upper = mu + n_std * std

    if X_test_1d is not None:
        line_mean, = ax.plot(X_test_1d, mu, color=color_mean, linewidth=2,
                             label=labels.get('mean', 'Mean') if labels else 'Mean')
        ax.fill_between(X_test_1d, lower, upper, color=color_fill, alpha=alpha_fill,
                        label=labels.get('uncertainty', f'{n_std}σ Confidence') if labels else f'{n_std}σ Confidence')
    else:
        line_mean = ax.plot(X_test, mu, color=color_mean, linewidth=2,
                            label=labels.get('mean', 'Mean') if labels else 'Mean')
        ax.fill_between(X_test.ravel(), lower, upper, color=color_fill, alpha=alpha_fill,
                        label=labels.get('uncertainty', f'{n_std}σ Confidence') if labels else f'{n_std}σ Confidence')

    if X_train is not None and y_train is not None:
        X_train = np.asarray(X_train)
        y_train = np.asarray(y_train)
        if X_train.ndim == 1:
            X_train = X_train.reshape(-1, 1)

        if X_train.shape[1] == 1:
            ax.scatter(X_train.ravel(), y_train, color='C3', s=30, edgecolors='k', zorder=5,
                       label=labels.get('data', 'Training Data') if labels else 'Training Data')
        else:
            ax.scatter(X_train, y_train, color='C3', s=30, edgecolors='k', zorder=5,
                       label=labels.get('data', 'Training Data') if labels else 'Training Data')

    if show_inducing and hasattr(gp, 'X_inducing') and gp.X_inducing is not None:
        X_ind = gp.X_inducing
        if X_ind.shape[1] == 1:
            y_min, y_max = ax.get_ylim()
            y_mid = (y_min + y_max) / 2
            ax.scatter(X_ind.ravel(), np.full(len(X_ind), y_mid),
                       marker='^', s=80, color='C2', edgecolors='k', zorder=6,
                       label=labels.get('inducing', 'Inducing Points') if labels else 'Inducing Points')
        else:
            ax.scatter(X_ind[:, 0], X_ind[:, 1],
                       marker='^', s=80, color='C2', edgecolors='k', zorder=6,
                       label=labels.get('inducing', 'Inducing Points') if labels else 'Inducing Points')

    if show_samples:
        try:
            from .predict import sample_y
            samples = sample_y(gp, X_test, n_samples=n_samples)
            if X_test_1d is not None:
                for i in range(n_samples):
                    ax.plot(X_test_1d, samples[:, i], color=color_mean, alpha=0.3,
                            linewidth=1, label=labels.get('samples', '') if i == 0 and labels else '')
            else:
                for i in range(n_samples):
                    ax.plot(X_test, samples[:, i], color=color_mean, alpha=0.3,
                            linewidth=1)
        except Exception:
            pass

    if true_func is not None and X_test_1d is not None:
        y_true = true_func(X_test_1d)
        ax.plot(X_test_1d, y_true, 'k--', linewidth=1.5, alpha=0.7,
                label=labels.get('true', 'True Function') if labels else 'True Function')

    if title is not None:
        ax.set_title(title, fontsize=14, fontweight='bold')
    if xlabel is not None:
        ax.set_xlabel(xlabel, fontsize=12)
    if ylabel is not None:
        ax.set_ylabel(ylabel, fontsize=12)

    if legend:
        ax.legend(loc='best', fontsize=10)

    ax.grid(True, alpha=0.3, linestyle='--')

    return ax


def compare_gp_models(
    models,
    X_test,
    X_train=None,
    y_train=None,
    n_std=2.0,
    model_names=None,
    figsize=(12, 8),
    **kwargs
):
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib is required for plotting.")

    fig, ax = plt.subplots(figsize=figsize)

    colors = plt.cm.tab10(np.linspace(0, 1, len(models)))

    for i, (gp, color) in enumerate(zip(models, colors)):
        X_test_arr = np.asarray(X_test)
        if X_test_arr.ndim == 1:
            X_test_arr = X_test_arr.reshape(-1, 1)

        mu, std = predict(gp, X_test_arr, return_std=True, return_cov=False)

        lower = mu - n_std * std
        upper = mu + n_std * std

        name = model_names[i] if model_names else f'Model {i + 1}'

        if X_test_arr.shape[1] == 1:
            ax.plot(X_test_arr.ravel(), mu, color=color, linewidth=2, label=name)
            ax.fill_between(X_test_arr.ravel(), lower, upper, color=color, alpha=0.15)

    if X_train is not None and y_train is not None:
        X_train_arr = np.asarray(X_train)
        if X_train_arr.ndim == 1:
            X_train_arr = X_train_arr.reshape(-1, 1)
        if X_train_arr.shape[1] == 1:
            ax.scatter(X_train_arr.ravel(), y_train, color='C3', s=30,
                       edgecolors='k', zorder=5, label='Training Data')

    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')

    return fig, ax


def plot_noise_estimation(
    gp,
    X_train,
    y_train,
    ax=None,
    figsize=(10, 5),
    **kwargs
):
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib is required for plotting.")

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    X_train = np.asarray(X_train)
    if X_train.ndim == 1:
        X_train = X_train.reshape(-1, 1)

    noise = gp.get_diag_noise()

    if hasattr(gp, 'is_sparse') and gp.is_sparse():
        label = 'FITC Noise (Lambda)'
    else:
        label = f'Noise ($\\sigma_n^2 = {gp.sigma_n ** 2:.4f}$)'

    if X_train.shape[1] == 1:
        ax.scatter(X_train.ravel(), noise, c='C4', s=40, alpha=0.7, label=label)
        ax.set_ylabel('Noise Estimate', fontsize=12)
        ax.set_xlabel('X', fontsize=12)
    else:
        ax.scatter(range(len(noise)), noise, c='C4', s=40, alpha=0.7, label=label)
        ax.set_ylabel('Noise Estimate', fontsize=12)
        ax.set_xlabel('Data Point Index', fontsize=12)

    ax.axhline(y=np.mean(noise), color='k', linestyle='--', linewidth=1, alpha=0.5, label='Mean Noise')

    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')

    return ax


def plot_kernel_matrix(
    gp,
    X,
    ax=None,
    figsize=(8, 8),
    cmap='viridis',
    add_noise=True,
    **kwargs
):
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib is required for plotting.")

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    X = np.asarray(X)
    if X.ndim == 1:
        X = X.reshape(-1, 1)

    K = gp.covariance_matrix(X, X, add_noise=add_noise)

    im = ax.imshow(K, cmap=cmap, aspect='equal')
    plt.colorbar(im, ax=ax, label='Covariance')

    ax.set_title('Kernel Matrix Heatmap', fontsize=14, fontweight='bold')
    ax.set_xlabel('Input Index', fontsize=12)
    ax.set_ylabel('Input Index', fontsize=12)

    return ax
