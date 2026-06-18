<?php
/**
 * Kategori / subdomain SEO içerik bloğu (sayfa altı, gömülü)
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

add_action('init', function () {
    register_term_meta('companion_category', 'hive_seo_body', array(
        'type'         => 'string',
        'single'       => true,
        'show_in_rest' => true,
    ));
    register_term_meta('story_category', 'hive_seo_body', array(
        'type'         => 'string',
        'single'       => true,
        'show_in_rest' => true,
    ));
    register_post_meta('page', '_hive_category_term_id', array(
        'type'         => 'integer',
        'single'       => true,
        'show_in_rest' => true,
    ));
});

/**
 * Sayfa içinde kategori ilanları: [hive_category_profiles term_id="123" limit="6"]
 */
add_shortcode('hive_category_profiles', function ($atts) {
    $atts = shortcode_atts(array(
        'term_id' => 0,
        'limit'   => 6,
    ), $atts, 'hive_category_profiles');
    $term_id = (int) $atts['term_id'];
    if (!$term_id) {
        return '';
    }
    $term = get_term($term_id, 'companion_category');
    if (!$term || is_wp_error($term)) {
        return '';
    }
    ob_start();
    hive_render_category_featured_profiles($term, (int) $atts['limit']);
    return ob_get_clean();
});

/**
 * Kategori SEO metni
 */
function hive_get_term_seo_body($term_id) {
    $body = get_term_meta($term_id, 'hive_seo_body', true);
    if ($body) {
        return $body;
    }
    $term = get_term($term_id);
    if ($term && !is_wp_error($term) && function_exists('hive_build_fallback_seo_body')) {
        return hive_build_fallback_seo_body($term->name, $term->slug);
    }
    return '';
}

/**
 * Subdomain / site SEO metni
 */
function hive_get_site_seo_body() {
    $body = get_option('hive_site_seo_body', '');
    if ($body) {
        return $body;
    }
    if (function_exists('hive_build_fallback_seo_body')) {
        $slug = '';
        if (is_multisite()) {
            $details = get_blog_details(get_current_blog_id());
            if ($details && !empty($details->domain)) {
                $slug = str_replace('.balkutusu.com', '', $details->domain);
            }
        }
        $title = $slug ? ucwords(str_replace('-', ' ', $slug)) . ' Kuşadası' : get_bloginfo('name');
        return hive_build_fallback_seo_body($title, $slug ?: 'kusadasi');
    }
    return '';
}

/**
 * Yedek kısa üretim (script çalışmamışsa)
 */
function hive_build_fallback_seo_body($title, $slug) {
    $kw = $title;
    $parts = array();
    for ($i = 0; $i < 12; $i++) {
        $parts[] = '<p>' . sprintf(
            esc_html__('Kuşadası %1$s rehberi: %2$s hizmetleri, escort profilleri, rezervasyon ve güvenilir iletişim. Ege kıyısında %3$s arayan ziyaretçiler için güncel bilgiler, mahalle bazlı öneriler ve VIP seçenekler tek adreste sunulur.', 'hive-ultra-premium'),
            esc_html($kw),
            esc_html($kw),
            esc_html($kw)
        ) . '</p>';
    }
    return implode("\n", $parts);
}

/**
 * Sayfa altı SEO bloğu – details ile kapalı, rahatsız etmez
 */
function hive_render_seo_footer_block($title, $html) {
    if (!$html || !trim(wp_strip_all_tags($html))) {
        return;
    }
    get_template_part('template-parts/seo-footer', 'block', array(
        'title'   => $title,
        'content' => $html,
    ));
}

/**
 * Kategori arşivinde üstte görünen tam içerik (H2/H3/SSS)
 */
function hive_render_category_landing_content($term = null) {
    if (!$term) {
        $term = get_queried_object();
    }
    if (!$term || is_wp_error($term)) {
        return;
    }
    $body = hive_get_term_seo_body($term->term_id);
    if (!$body || !trim(wp_strip_all_tags($body))) {
        return;
    }
    ?>
    <article class="category-landing-content entry-content" aria-label="<?php echo esc_attr($term->name); ?>">
        <?php echo wp_kses_post($body); ?>
    </article>
    <?php
    hive_output_faq_schema_from_html($body);
}

/**
 * Kategori sayfasında öne çıkan ilanlar (üst grid)
 */
function hive_render_category_featured_profiles($term = null, $limit = 6) {
    if (!$term) {
        $term = get_queried_object();
    }
    if (!$term || is_wp_error($term)) {
        return;
    }
    $q = new WP_Query(array(
        'post_type'      => 'companion_profile',
        'posts_per_page' => max(1, min(12, (int) $limit)),
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
        return;
    }
    ?>
    <section class="category-featured-profiles" aria-label="<?php esc_attr_e('Öne çıkan ilanlar', 'hive-ultra-premium'); ?>">
        <h2 class="category-featured-title"><?php echo esc_html(sprintf(__('Öne Çıkan %s İlanları', 'hive-ultra-premium'), $term->name)); ?></h2>
        <div class="profiles-photo-grid category-featured-grid">
            <?php
            while ($q->have_posts()) :
                $q->the_post();
                get_template_part('template-parts/profile', 'grid-thumb', array('post' => get_post()));
            endwhile;
            wp_reset_postdata();
            ?>
        </div>
    </section>
    <?php
}

/**
 * HTML içinden SSS başlıklarını FAQPage schema olarak çıkar
 */
function hive_output_faq_schema_from_html($html) {
    if (!preg_match_all('/<h3[^>]*>(.*?)<\/h3>\s*<p[^>]*>(.*?)<\/p>/is', $html, $m, PREG_SET_ORDER)) {
        return;
    }
    $entities = array();
    foreach (array_slice($m, 0, 12) as $row) {
        $q = wp_strip_all_tags($row[1]);
        $a = wp_strip_all_tags($row[2]);
        if ($q && $a) {
            $entities[] = array(
                '@type'          => 'Question',
                'name'           => $q,
                'acceptedAnswer' => array(
                    '@type' => 'Answer',
                    'text'  => $a,
                ),
            );
        }
    }
    if (!$entities) {
        return;
    }
    $schema = array(
        '@context'   => 'https://schema.org',
        '@type'      => 'FAQPage',
        'mainEntity' => $entities,
    );
    echo '<script type="application/ld+json">' . wp_json_encode($schema, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . '</script>';
}

function hive_render_category_seo_footer() {
    /* Tam içerik artık üstte gösteriliyor; alt tekrar yok */
}

function hive_render_site_seo_footer() {
    if (!is_front_page()) {
        return;
    }
    $body = hive_get_site_seo_body();
    $title = is_multisite() && !hive_is_main_site()
        ? sprintf(__('Kuşadası %s Escort Rehberi', 'hive-ultra-premium'), get_bloginfo('name'))
        : __('Kuşadası Escort & Arkadaşlık Rehberi', 'hive-ultra-premium');
    hive_render_seo_footer_block($title, $body);
}
