from .dcgan import DCGANGenerator, DCGANDiscriminator
from .wgangp import WGGANGenerator, WGGANCritic, compute_gradient_penalty
from .stylegan2 import StyleGAN2Generator, StyleGAN2Discriminator

ARCHITECTURES = {
    "dcgan": {
        "generator": DCGANGenerator,
        "discriminator": DCGANDiscriminator,
    },
    "wgan-gp": {
        "generator": WGGANGenerator,
        "discriminator": WGGANCritic,
    },
    "stylegan2": {
        "generator": StyleGAN2Generator,
        "discriminator": StyleGAN2Discriminator,
    },
}


def build_models(config):
    arch = ARCHITECTURES.get(config.architecture)
    if arch is None:
        raise ValueError(f"Unknown architecture: {config.architecture}. Available: {list(ARCHITECTURES.keys())}")

    if config.architecture == "dcgan":
        g = arch["generator"](
            z_dim=config.z_dim,
            img_channels=config.img_channels,
            base_channels=config.g_base_channels,
            img_size=config.img_size,
        )
        d = arch["discriminator"](
            img_channels=config.img_channels,
            base_channels=config.d_base_channels,
            img_size=config.img_size,
            use_spectral_norm=config.d_spectral_norm,
        )
    elif config.architecture == "wgan-gp":
        g = arch["generator"](
            z_dim=config.z_dim,
            img_channels=config.img_channels,
            base_channels=config.g_base_channels,
            img_size=config.img_size,
        )
        d = arch["discriminator"](
            img_channels=config.img_channels,
            base_channels=config.d_base_channels,
            img_size=config.img_size,
            use_spectral_norm=config.d_spectral_norm,
        )
    elif config.architecture == "stylegan2":
        g = arch["generator"](
            z_dim=config.z_dim,
            img_channels=config.img_channels,
            style_dim=config.style_dim,
            base_channels=config.g_base_channels,
            img_size=config.img_size,
            n_layers_style=config.n_layers_style,
            use_sn=config.g_spectral_norm,
            mapping_dropout=config.mapping_dropout,
        )
        d = arch["discriminator"](
            img_channels=config.img_channels,
            style_dim=config.style_dim,
            base_channels=config.d_base_channels,
            img_size=config.img_size,
            use_sn=config.d_spectral_norm,
        )
    else:
        raise ValueError(f"Unhandled architecture: {config.architecture}")

    return g, d
