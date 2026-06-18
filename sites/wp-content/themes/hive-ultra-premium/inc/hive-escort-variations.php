<?php
/**
 * Kuşadası escort varyasyon kategorileri + subdomain eşlemesi
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

add_action('init', function () {
    foreach (array('hive_cat_group', 'hive_geo_mahalle', 'hive_geo_street', 'hive_variant', 'hive_loc_type', 'hive_porn_label', 'hive_porn_lang', 'hive_porn_pair') as $key) {
        register_term_meta('companion_category', $key, array(
            'type'         => 'string',
            'single'       => true,
            'show_in_rest' => true,
        ));
    }
});

/**
 * Tüm escort tip / uyruk / hizmet varyasyonları
 *
 * @return array<int, array{0: string, 1: string}>
 */
function hive_escort_variation_definitions() {
    $types = array(
        'turk-escort', 'rus-escort', 'ukraynali-escort', 'moldovali-escort', 'yabanci-escort',
        'beyaz-rus-escort', 'gurcu-escort', 'romen-escort', 'bulgar-escort', 'kazak-escort',
        'ingilizce-escort', 'rusca-escort', 'almanca-escort', 'arapca-escort', 'fransizca-escort',
        'vip-escort', 'premium-escort', 'luks-escort', 'luxury-escort', 'elite-escort', 'ucuz-escort',
        'genc-escort', 'yetiskin-escort', 'olgun-escort', 'orta-yas-escort',
        'sarisin-escort', 'esmer-escort', 'kizil-escort', 'kumral-escort', 'uzun-boylu-escort',
        'minyon-escort', 'dolgun-escort', 'fit-escort', 'zayif-escort',
        'anal-escort', 'oral-escort', 'otel-escort', 'plaj-escort', 'gece-escort',
        '24saat-escort', 'masaj-escort', 'cift-escort', 'grup-escort',
        'eve-gelen-escort', 'otele-gelen-escort', 'jakuzili-escort', 'fantezi-escort',
        'vip-model', 'premium-model', 'kusadasi-escort', 'aydin-escort', 'ege-escort',
    );

    $labels = array(
        'turk-escort'        => 'Kuşadası Türk Escort',
        'rus-escort'         => 'Kuşadası Rus Escort',
        'ukraynali-escort'   => 'Kuşadası Ukraynalı Escort',
        'moldovali-escort'   => 'Kuşadası Moldovalı Escort',
        'yabanci-escort'     => 'Kuşadası Yabancı Escort',
        'beyaz-rus-escort'   => 'Kuşadası Beyaz Rus Escort',
        'gurcu-escort'       => 'Kuşadası Gürcü Escort',
        'romen-escort'       => 'Kuşadası Romen Escort',
        'bulgar-escort'      => 'Kuşadası Bulgar Escort',
        'kazak-escort'       => 'Kuşadası Kazak Escort',
        'ingilizce-escort'   => 'Kuşadası İngilizce Escort',
        'rusca-escort'       => 'Kuşadası Rusça Escort',
        'almanca-escort'     => 'Kuşadası Almanca Escort',
        'arapca-escort'      => 'Kuşadası Arapça Escort',
        'fransizca-escort'   => 'Kuşadası Fransızca Escort',
        'vip-escort'         => 'Kuşadası VIP Escort',
        'premium-escort'     => 'Kuşadası Premium Escort',
        'luks-escort'        => 'Kuşadası Lüks Escort',
        'luxury-escort'      => 'Kuşadası Luxury Escort',
        'elite-escort'       => 'Kuşadası Elite Escort',
        'ucuz-escort'        => 'Kuşadası Ucuz Escort',
        'genc-escort'        => 'Kuşadası Genç Escort',
        'yetiskin-escort'    => 'Kuşadası Yetişkin Escort',
        'olgun-escort'       => 'Kuşadası Olgun Escort',
        'orta-yas-escort'    => 'Kuşadası Orta Yaş Escort',
        'sarisin-escort'     => 'Kuşadası Sarışın Escort',
        'esmer-escort'       => 'Kuşadası Esmer Escort',
        'kizil-escort'       => 'Kuşadası Kızıl Escort',
        'kumral-escort'      => 'Kuşadası Kumral Escort',
        'uzun-boylu-escort'  => 'Kuşadası Uzun Boylu Escort',
        'minyon-escort'      => 'Kuşadası Minyon Escort',
        'dolgun-escort'      => 'Kuşadası Dolgun Escort',
        'fit-escort'         => 'Kuşadası Fit Escort',
        'zayif-escort'       => 'Kuşadası Zayıf Escort',
        'anal-escort'        => 'Kuşadası Anal Escort',
        'oral-escort'        => 'Kuşadası Oral Escort',
        'otel-escort'        => 'Kuşadası Otel Escort',
        'plaj-escort'        => 'Kuşadası Plaj Escort',
        'gece-escort'        => 'Kuşadası Gece Escort',
        '24saat-escort'      => 'Kuşadası 24 Saat Escort',
        'masaj-escort'       => 'Kuşadası Masaj Escort',
        'cift-escort'        => 'Kuşadası Çift Escort',
        'grup-escort'        => 'Kuşadası Grup Escort',
        'eve-gelen-escort'   => 'Kuşadası Eve Gelen Escort',
        'otele-gelen-escort' => 'Kuşadası Otele Gelen Escort',
        'jakuzili-escort'    => 'Kuşadası Jakuzili Escort',
        'fantezi-escort'     => 'Kuşadası Fantezi Escort',
        'vip-model'          => 'Kuşadası VIP Model Escort',
        'premium-model'      => 'Kuşadası Premium Model Escort',
        'kusadasi-escort'    => 'Kuşadası Escort',
        'aydin-escort'       => 'Kuşadası Aydın Escort',
        'ege-escort'         => 'Kuşadası Ege Escort',
    );

    $out = array();
    foreach ($types as $slug) {
        $name = isset($labels[$slug]) ? $labels[$slug] : ('Kuşadası ' . ucwords(str_replace('-', ' ', $slug)));
        $out[] = array($slug, $name);
    }
    return $out;
}

function hive_subdomain_slug() {
    if (!is_multisite() || hive_is_main_site()) {
        return '';
    }
    $details = get_blog_details(get_current_blog_id());
    if (!$details || empty($details->domain)) {
        return '';
    }
    return str_replace('.balkutusu.com', '', $details->domain);
}

/**
 * Subdomain slug → companion_category term
 */
function hive_variation_term_for_slug($slug) {
    if (!$slug) {
        return null;
    }
    $term = get_term_by('slug', $slug, 'companion_category');
    if ($term && !is_wp_error($term)) {
        return $term;
    }
    $alt = preg_replace('/-escort$/', '', $slug);
    if ($alt && $alt !== $slug) {
        $term = get_term_by('slug', $alt . '-escort', 'companion_category');
        if ($term && !is_wp_error($term)) {
            return $term;
        }
    }
    return null;
}

/**
 * Escort tipi kategorisi mi?
 */
function hive_is_escort_tip_term($term) {
    if (!$term || is_wp_error($term)) {
        return false;
    }
    if (get_term_meta($term->term_id, 'hive_cat_group', true) === 'escort_tip') {
        return true;
    }
    static $slugs = null;
    if ($slugs === null) {
        $slugs = array_column(hive_escort_variation_definitions(), 0);
    }
    return in_array($term->slug, $slugs, true);
}

/**
 * Escort tipi kategorileri (mahalle hariç)
 */
function hive_get_escort_tip_categories() {
    $all = hive_get_valid_categories(array(
        'parent'     => 0,
        'hide_empty' => false,
        'orderby'    => 'name',
        'order'      => 'ASC',
        'number'     => 0,
    ));
    return array_values(array_filter($all, 'hive_is_escort_tip_term'));
}

/**
 * Mahalle parent kategorileri
 */
function hive_get_mahalle_categories() {
    $all = hive_get_valid_categories(array(
        'parent'     => 0,
        'hide_empty' => false,
        'orderby'    => 'name',
        'order'      => 'ASC',
    ));
    return array_values(array_filter($all, function ($term) {
        $group = get_term_meta($term->term_id, 'hive_cat_group', true);
        if ($group === 'mahalle') {
            return true;
        }
        if (in_array($group, array('escort_tip', 'porn_en', 'porn_tr'), true) || hive_is_escort_tip_term($term)) {
            return false;
        }
        return hive_category_has_children($term->term_id);
    }));
}

function hive_render_escort_tip_hub() {
    $terms = hive_get_escort_tip_categories();
    if (empty($terms)) {
        return;
    }
    echo '<section class="category-hub-section">';
    echo '<h2 class="category-hub-section-title">' . esc_html__('Kuşadası Escort Tipleri', 'hive-ultra-premium') . '</h2>';
    echo '<p class="category-hub-section-desc">' . esc_html__('Türk, Rus, VIP, genç, otel ve daha fazlası — ilanlar rastgele güncellenir.', 'hive-ultra-premium') . '</p>';
    echo '<div class="category-hub-grid category-hub-grid-tips">';
    foreach ($terms as $term) {
        $link = get_term_link($term);
        if (is_wp_error($link)) {
            continue;
        }
        $count = (int) $term->count;
        echo '<a class="category-hub-card category-hub-card-tip" href="' . esc_url($link) . '">';
        echo '<h3 class="category-hub-name">' . esc_html($term->name) . '</h3>';
        if ($count > 0) {
            echo '<span class="category-hub-meta">' . esc_html(sprintf(__('%d ilan', 'hive-ultra-premium'), $count)) . '</span>';
        }
        echo '</a>';
    }
    echo '</div></section>';
}

function hive_render_mahalle_hub() {
    $terms = hive_get_mahalle_categories();
    if (empty($terms)) {
        hive_render_category_hub();
        return;
    }
    echo '<section class="category-hub-section">';
    echo '<h2 class="category-hub-section-title">' . esc_html__('Mahalleler', 'hive-ultra-premium') . '</h2>';
    echo '<div class="category-hub-grid">';
    foreach ($terms as $term) {
        $link = get_term_link($term);
        if (is_wp_error($link)) {
            continue;
        }
        $child_count = count(hive_get_valid_categories(array('parent' => $term->term_id)));
        echo '<a class="category-hub-card" href="' . esc_url($link) . '">';
        echo '<h3 class="category-hub-name">' . esc_html($term->name) . '</h3>';
        echo '<span class="category-hub-meta">' . esc_html(sprintf(__('%d alt kategori', 'hive-ultra-premium'), $child_count)) . '</span>';
        echo '</a>';
    }
    echo '</div></section>';
}

/**
 * Subdomain / kategori sayfası – bu varyasyona atanmış ilanlar
 */
function hive_render_variation_profile_slider($term = null, $title = '') {
    if (!$term) {
        $slug = hive_subdomain_slug();
        if ($slug) {
            hive_on_main_blog_for_feed(function () use ($slug, $title) {
                $t = hive_variation_term_for_slug($slug);
                if ($t) {
                    hive_render_variation_profile_slider($t, $title);
                }
            });
        }
        return;
    }

    $q = new WP_Query(array(
        'post_type'      => 'companion_profile',
        'posts_per_page' => 14,
        'orderby'        => 'rand',
        'tax_query'      => array(
            array(
                'taxonomy' => 'companion_category',
                'field'    => 'term_id',
                'terms'    => $term->term_id,
            ),
        ),
    ));

    if (!$q->have_posts()) {
        $q = new WP_Query(array(
            'post_type'      => 'companion_profile',
            'posts_per_page' => 14,
            'orderby'        => 'rand',
        ));
    }

    $slide_title = $title ?: ('📍 ' . $term->name . ' — ' . __('İlanlar', 'hive-ultra-premium'));
    get_template_part('template-parts/slide', 'section', array(
        'title' => $slide_title,
        'query' => $q,
    ));
}
