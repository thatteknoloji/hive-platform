<?php
/**
 * Front page – Hero, profil şeritleri, swipe & hikayeler altta
 *
 * @package Hive_Ultra_Premium
 */

get_header();

$hero_bg      = get_theme_mod('hive_hero_background', '');
$hero_style   = $hero_bg ? ' style="background-image: url(' . esc_url($hero_bg) . ');"' : '';
$hero_video   = HIVE_ULTRA_URI . '/assets/video/hero-bg.webm';
$hero_video_m = HIVE_ULTRA_URI . '/assets/video/hero-bg.mp4';
$has_hero_vid = file_exists(HIVE_ULTRA_DIR . '/assets/video/hero-bg.webm')
    || file_exists(HIVE_ULTRA_DIR . '/assets/video/hero-bg.mp4');
$hero_class   = 'hero' . ($has_hero_vid ? ' hero--video' : '');
?>

<section class="<?php echo esc_attr($hero_class); ?>"<?php echo $hero_style; ?>>
    <?php if ($has_hero_vid) : ?>
        <video class="hero-video" autoplay muted loop playsinline preload="metadata" aria-hidden="true">
            <?php if (file_exists(HIVE_ULTRA_DIR . '/assets/video/hero-bg.webm')) : ?>
                <source src="<?php echo esc_url($hero_video); ?>" type="video/webm">
            <?php endif; ?>
            <?php if (file_exists(HIVE_ULTRA_DIR . '/assets/video/hero-bg.mp4')) : ?>
                <source src="<?php echo esc_url($hero_video_m); ?>" type="video/mp4">
            <?php endif; ?>
        </video>
    <?php endif; ?>
    <div class="hero-overlay" aria-hidden="true"></div>
    <div class="hero-content">
        <p class="hero-eyebrow"><?php esc_html_e('Bal Kutusu — Kuşadası Escort Rehberi', 'hive-ultra-premium'); ?></p>
        <h1 class="hero-title"><?php esc_html_e('Kuşadası\'nda Premium Arkadaşlık Deneyimi', 'hive-ultra-premium'); ?></h1>
        <h2 class="hero-tagline"><?php esc_html_e('Kuşadası\'nın En Seçkin VIP Escort Profilleri', 'hive-ultra-premium'); ?></h2>
        <h3 class="hero-subtitle"><?php esc_html_e('Kuşadası escort hizmetleri, özel anlar ve güvenilir buluşmalar — tek adreste.', 'hive-ultra-premium'); ?></h3>

        <?php
        $ilan_phone      = get_theme_mod('hive_ilan_contact_phone', '0xxx xxx xx xx');
        $ilan_phone_tel  = preg_replace('/\D+/', '', $ilan_phone);
        ?>
        <div class="hero-contact-cta" role="note">
            <span class="hero-contact-pulse" aria-hidden="true"></span>
            <p class="hero-contact-text">
                <span class="hero-contact-label"><?php esc_html_e('İlanlarınızı Yayınlamak İçin İletişim Bilgimiz', 'hive-ultra-premium'); ?></span>
                <?php if ($ilan_phone_tel) : ?>
                    <a href="<?php echo esc_url('tel:' . $ilan_phone_tel); ?>" class="hero-contact-phone"><?php echo esc_html($ilan_phone); ?></a>
                <?php else : ?>
                    <strong class="hero-contact-phone"><?php echo esc_html($ilan_phone); ?></strong>
                <?php endif; ?>
            </p>
        </div>

        <a href="<?php echo esc_url(get_post_type_archive_link('companion_profile')); ?>" class="btn btn-primary">
            <?php esc_html_e('Kuşadası Profillerini Keşfet', 'hive-ultra-premium'); ?>
        </a>
        <?php if (function_exists('hive_render_unified_search')) : ?>
            <div class="hero-search">
                <?php hive_render_unified_search(array(
                    'id'          => 'hive-hero-search',
                    'live'        => true,
                    'placeholder' => __('İlan adı, Telegram kullanıcı adı, kategori veya lokasyon ara…', 'hive-ultra-premium'),
                )); ?>
            </div>
        <?php endif; ?>
    </div>
</section>

<main id="main-content" class="site-main home-feed">
    <div class="container">

        <?php get_template_part('template-parts/stories', 'slider'); ?>

        <?php
        if (function_exists('hive_render_home_profile_feed')) {
            hive_render_home_profile_feed();
        }
        ?>

        <?php get_template_part('template-parts/category', 'grid', array('limit' => 18)); ?>

        <?php
        $categories = function_exists('hive_get_valid_categories')
            ? hive_get_valid_categories(array(
                'hide_empty' => true,
                'number'     => 6,
                'parent'     => 0,
            ))
            : get_terms(array(
                'taxonomy'   => 'companion_category',
                'hide_empty' => true,
                'number'     => 6,
                'parent'     => 0,
            ));

        if (!is_wp_error($categories) && !empty($categories)) {
            foreach ($categories as $category) {
                $cat_query = new WP_Query(array(
                    'post_type'      => 'companion_profile',
                    'posts_per_page' => 18,
                    'tax_query'      => array(
                        array(
                            'taxonomy' => 'companion_category',
                            'field'    => 'term_id',
                            'terms'    => $category->term_id,
                        ),
                    ),
                ));
                if (!$cat_query->have_posts()) {
                    continue;
                }
                get_template_part('template-parts/slide', 'section', array(
                    'title' => $category->name,
                    'query' => $cat_query,
                    'cols'  => 6,
                ));
            }
        }
        ?>

        <?php get_template_part('template-parts/hive', 'swipe-section'); ?>

        <?php get_template_part('template-parts/erotic-stories', 'slider'); ?>

        <?php
        if (function_exists('hive_render_site_seo_footer')) {
            hive_render_site_seo_footer();
        }
        ?>

    </div>
</main>

<?php get_footer(); ?>
