<?php
/**
 * Ana sayfa profil şeritleri (ana site + subdomain aynı ilanlar)
 *
 * @package Hive_Ultra_Premium
 */

$archive_url = hive_main_profiles_archive_url();

$vip_query = new WP_Query(array(
    'post_type'      => 'companion_profile',
    'posts_per_page' => 18,
    'meta_key'       => 'vip',
    'meta_value'     => '1',
    'orderby'        => 'date',
    'order'          => 'DESC',
));
if (!$vip_query->have_posts()) {
    $vip_query = new WP_Query(array(
        'post_type'      => 'companion_profile',
        'posts_per_page' => 18,
        'orderby'        => 'rand',
    ));
}
get_template_part('template-parts/slide', 'section', array(
    'title' => '⭐ ' . __('VIP Profiller', 'hive-ultra-premium'),
    'query' => $vip_query,
    'cols'  => 6,
));

$populer_query = new WP_Query(array(
    'post_type'      => 'companion_profile',
    'posts_per_page' => 18,
    'orderby'        => 'rand',
    'meta_query'     => array(
        array('key' => 'fiyat', 'compare' => 'EXISTS'),
    ),
));
get_template_part('template-parts/slide', 'section', array(
    'title' => '🔥 ' . __('Popüler', 'hive-ultra-premium'),
    'query' => $populer_query,
    'cols'  => 6,
));

$yeni_query = new WP_Query(array(
    'post_type'      => 'companion_profile',
    'posts_per_page' => 18,
    'orderby'        => 'date',
    'order'          => 'DESC',
));
get_template_part('template-parts/slide', 'section', array(
    'title' => '🆕 ' . __('Yeni Eklenenler', 'hive-ultra-premium'),
    'query' => $yeni_query,
    'cols'  => 6,
));

$ikili_query = new WP_Query(array(
    'post_type'      => 'companion_profile',
    'posts_per_page' => 18,
    'orderby'        => 'rand',
    'meta_query'     => array(
        'relation' => 'OR',
        array('key' => 'ozellikler', 'value' => 'çift', 'compare' => 'LIKE'),
        array('key' => 'ozellikler', 'value' => 'cift', 'compare' => 'LIKE'),
        array('key' => 'hizmetler', 'value' => 'cift', 'compare' => 'LIKE'),
    ),
));
if (!$ikili_query->have_posts()) {
    $ikili_query = new WP_Query(array(
        'post_type'      => 'companion_profile',
        'posts_per_page' => 18,
        'orderby'        => 'rand',
    ));
}
get_template_part('template-parts/slide', 'section', array(
    'title' => '👯 ' . __("2'li Arkadaşlar", 'hive-ultra-premium'),
    'query' => $ikili_query,
    'cols'  => 6,
));

$uclu_query = new WP_Query(array(
    'post_type'      => 'companion_profile',
    'posts_per_page' => 18,
    'orderby'        => 'rand',
    'meta_query'     => array(
        'relation' => 'OR',
        array('key' => 'ozellikler', 'value' => 'grup', 'compare' => 'LIKE'),
        array('key' => 'hizmetler', 'value' => 'grup', 'compare' => 'LIKE'),
        array('key' => 'ozellikler', 'value' => 'partner', 'compare' => 'LIKE'),
    ),
));
if (!$uclu_query->have_posts()) {
    $uclu_query = new WP_Query(array(
        'post_type'      => 'companion_profile',
        'posts_per_page' => 18,
        'orderby'        => 'rand',
        'offset'         => 12,
    ));
}
get_template_part('template-parts/slide', 'section', array(
    'title' => '👥 ' . __("3'lü Arkadaşlar", 'hive-ultra-premium'),
    'query' => $uclu_query,
    'cols'  => 6,
));
?>

<div class="section-header home-feed-cta">
    <a href="<?php echo esc_url($archive_url); ?>" class="btn btn-secondary">
        <?php esc_html_e('Tüm Profilleri Gör', 'hive-ultra-premium'); ?>
    </a>
</div>
