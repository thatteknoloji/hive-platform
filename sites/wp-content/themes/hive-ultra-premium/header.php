<?php
/**
 * Header template
 *
 * @package Hive_Ultra_Premium
 */
?><!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
<?php if (function_exists('hive_render_head_injections')) { hive_render_head_injections(); } ?>
    <meta charset="<?php bloginfo('charset'); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="profile" href="https://gmpg.org/xfn/11">
    <?php if (is_front_page()) : ?>
    <meta name="description" content="Kuşadası escort, vip model escort bayanlar, otel escort ve gece hayatı rehberi. En güzel ve kaliteli escortlar burada.">
    <meta name="keywords" content="kuşadası escort, vip escort, otel escort, kadınlar denizi escort, yılancı burnu escort">
    <?php elseif (is_singular('companion_profile')) : ?>
    <meta name="description" content="<?php echo esc_attr(get_the_title()); ?> - Kuşadası escort hizmetleri, fiyatları ve iletişim bilgileri.">
    <?php endif; ?>
    <script>
    (function(){try{var t=localStorage.getItem('hive-theme');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t);}catch(e){}})();
    </script>
    <?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>

<a class="skip-link" href="#main-content"><?php esc_html_e('İçeriğe atla', 'hive-ultra-premium'); ?></a>

<header class="site-header" role="banner">
    <div class="container header-inner">
        <div class="site-branding">
            <?php
            $logo_url = function_exists('hive_is_main_site') && !hive_is_main_site()
                ? hive_main_site_url()
                : home_url('/');
            ?>
            <a href="<?php echo esc_url($logo_url); ?>" rel="home" class="site-logo-link"<?php echo (function_exists('hive_is_main_site') && !hive_is_main_site()) ? ' title="' . esc_attr__('Bal Kutusu Ana Site — balkutusu.com', 'hive-ultra-premium') . '"' : ''; ?>>
                <img src="<?php echo esc_url(hive_brand_logo_url()); ?>" alt="<?php esc_attr_e('Bal Kutusu — Kuşadası Escort', 'hive-ultra-premium'); ?>" class="bal-kutusu-logo" width="340" height="76" decoding="async">
            </a>
        </div>

        <nav id="site-navigation" class="main-navigation" role="navigation" aria-label="<?php esc_attr_e('Ana menü', 'hive-ultra-premium'); ?>">
            <?php
            wp_nav_menu(array(
                'theme_location' => 'primary',
                'menu_id'        => 'primary-menu',
                'container'      => false,
                'fallback_cb'    => function () {
                    echo '<ul id="primary-menu">';
                    if (function_exists('hive_is_main_site') && !hive_is_main_site()) {
                        echo '<li><a href="' . esc_url(hive_main_site_url()) . '" class="main-portal-link">' . esc_html__('balkutusu.com', 'hive-ultra-premium') . '</a></li>';
                    }
                    echo '<li><a href="' . esc_url(home_url('/')) . '">' . esc_html__('Ana Sayfa', 'hive-ultra-premium') . '</a></li>';
                    echo '<li><a href="' . esc_url(get_post_type_archive_link('companion_profile')) . '">' . esc_html__('Profiller', 'hive-ultra-premium') . '</a></li>';
                    if (function_exists('hive_categories_page_url')) {
                        echo '<li><a href="' . esc_url(hive_categories_page_url()) . '">' . esc_html__('Kategoriler', 'hive-ultra-premium') . '</a></li>';
                    }
                    echo '<li><a href="' . esc_url(get_post_type_archive_link('erotic_story')) . '">' . esc_html__('Hikayeler', 'hive-ultra-premium') . '</a></li>';
                    echo '<li><a href="#" id="hive-fav-link">' . esc_html__('Favorilerim', 'hive-ultra-premium') . '</a></li>';
                    echo '</ul>';
                },
            ));
            ?>
            <button class="theme-toggle" id="theme-toggle" type="button" aria-label="<?php esc_attr_e('Tema değiştir', 'hive-ultra-premium'); ?>">🌙</button>
        </nav>

        <div class="header-actions">
            <?php if (function_exists('hive_render_unified_search')) : ?>
                <div class="header-search-wrap">
                    <?php hive_render_unified_search(array(
                        'id'          => 'hive-header-search',
                        'compact'     => true,
                        'live'        => true,
                        'placeholder' => __('İlan, kullanıcı adı, kategori…', 'hive-ultra-premium'),
                    )); ?>
                </div>
            <?php endif; ?>

            <button class="hive-cat-menu-btn" type="button" aria-expanded="false" aria-controls="hive-cat-drawer" aria-label="<?php esc_attr_e('Kategoriler menüsünü aç', 'hive-ultra-premium'); ?>">
                <span class="hive-cat-menu-icon" aria-hidden="true"><span></span><span></span><span></span></span>
                <span class="hive-cat-menu-label"><?php esc_html_e('Kategoriler', 'hive-ultra-premium'); ?></span>
            </button>

            <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="primary-menu" aria-label="<?php esc_attr_e('Menüyü aç/kapat', 'hive-ultra-premium'); ?>">
                <span></span><span></span><span></span>
            </button>
        </div>
    </div>
</header>
