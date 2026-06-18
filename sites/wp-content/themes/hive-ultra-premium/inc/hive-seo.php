<?php
/**
 * SEO, schema, breadcrumb, IndexNow
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

function hive_breadcrumb() {
    if (is_front_page()) {
        return;
    }
    $parts = array();
    $parts[] = '<a href="' . esc_url(home_url('/')) . '">' . esc_html__('Ana Sayfa', 'hive-ultra-premium') . '</a>';
    if (is_singular('companion_profile')) {
        $parts[] = '<a href="' . esc_url(get_post_type_archive_link('companion_profile')) . '">' . esc_html__('Profiller', 'hive-ultra-premium') . '</a>';
        $parts[] = '<span aria-current="page">' . esc_html(get_the_title()) . '</span>';
    } elseif (is_tax('companion_category')) {
        $term = get_queried_object();
        $parts[] = '<a href="' . esc_url(hive_categories_page_url()) . '">' . esc_html__('Kategoriler', 'hive-ultra-premium') . '</a>';
        if ($term->parent) {
            $parent = get_term($term->parent, 'companion_category');
            if ($parent && !is_wp_error($parent)) {
                $parts[] = '<a href="' . esc_url(get_term_link($parent)) . '">' . esc_html($parent->name) . '</a>';
            }
        }
        $parts[] = '<span aria-current="page">' . esc_html($term->name) . '</span>';
    } elseif (is_post_type_archive('companion_profile')) {
        $parts[] = '<span aria-current="page">' . esc_html__('Profiller', 'hive-ultra-premium') . '</span>';
    } else {
        $parts[] = '<span aria-current="page">' . esc_html(wp_get_document_title()) . '</span>';
    }
    echo '<nav class="hive-breadcrumb" aria-label="' . esc_attr__('Konum', 'hive-ultra-premium') . '"><div class="hive-breadcrumb-track">';
    echo implode('<span class="hive-breadcrumb-sep">›</span>', $parts);
    echo '</div></nav>';
}

add_action('wp_head', 'hive_al_geo_schema');
function hive_al_geo_schema() {
    if (is_singular('companion_profile')) {
        $n = get_the_title();
        $u = get_permalink();
        $i = get_the_post_thumbnail_url();
        ?>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Person","name":"<?php echo esc_js($n); ?>","url":"<?php echo esc_url($u); ?>","image":"<?php echo esc_url($i ?: hive_ultra_placeholder_url()); ?>","address":{"@type":"PostalAddress","addressLocality":"Kuşadası","addressRegion":"Aydın","addressCountry":"TR"},"knowsAbout":["Escort","VIP Hizmetler","Kuşadası","Gece Hayatı","Özel Rezervasyon"],"al":{"@type":"AuthoritativeLink","authority":"Google","link":"https://developers.google.com/search/docs/appearance/structured-data/article"},"geo":{"@type":"GeoCoordinates","latitude":"37.8662","longitude":"27.2666"}}
</script>
        <?php
    }
    if (is_front_page()) {
        ?>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"Kuşadası Escort","url":"<?php echo esc_url(home_url('/')); ?>","address":{"@type":"PostalAddress","addressLocality":"Kuşadası","addressRegion":"Aydın","addressCountry":"TR"},"geo":{"@type":"GeoCoordinates","latitude":"37.8662","longitude":"27.2666"}}
</script>
        <?php
    }
}

function hive_ping_indexnow() {
    if (!get_option('hive_indexnow_key')) {
        $key = wp_generate_password(32, false);
        update_option('hive_indexnow_key', $key);
        if (is_writable(ABSPATH)) {
            file_put_contents(ABSPATH . 'indexnow_key.txt', $key);
        }
    }
}
add_action('init', 'hive_ping_indexnow');

function hive_get_indexnow_key() {
    hive_ping_indexnow();
    return get_option('hive_indexnow_key');
}

/**
 * IndexNow toplu ping (Bing, Yandex, api.indexnow.org)
 */
function hive_indexnow_ping_urls($urls) {
    $key = hive_get_indexnow_key();
    if (!$key || empty($urls)) {
        return;
    }
    $urls = array_values(array_unique(array_filter($urls)));
    $host = wp_parse_url(home_url(), PHP_URL_HOST);
    $chunks = array_chunk($urls, 500);
    foreach ($chunks as $chunk) {
        wp_remote_post(
            'https://api.indexnow.org/indexnow',
            array(
                'timeout' => 15,
                'headers' => array('Content-Type' => 'application/json; charset=utf-8'),
                'body'    => wp_json_encode(array(
                    'host'        => $host,
                    'key'         => $key,
                    'keyLocation' => home_url('/indexnow_key.txt'),
                    'urlList'     => $chunk,
                )),
            )
        );
        foreach ($chunk as $u) {
            wp_remote_get('https://www.bing.com/indexnow?url=' . rawurlencode($u) . '&key=' . $key, array('blocking' => false, 'timeout' => 3));
            wp_remote_get('https://yandex.com/indexnow?url=' . rawurlencode($u) . '&key=' . $key, array('blocking' => false, 'timeout' => 3));
        }
    }
    $sitemap = home_url('/sitemap_index.xml');
    wp_remote_get('https://www.google.com/ping?sitemap=' . rawurlencode($sitemap), array('blocking' => false, 'timeout' => 5));
    wp_remote_get('https://www.bing.com/ping?sitemap=' . rawurlencode($sitemap), array('blocking' => false, 'timeout' => 5));
}

function hive_publish_ping($post_id) {
    hive_indexnow_ping_urls(array(get_permalink($post_id), home_url('/sitemap_index.xml')));
}
add_action('publish_companion_profile', 'hive_publish_ping');
add_action('publish_page', 'hive_publish_ping');
add_action('edited_companion_category', 'hive_term_reindex_ping', 10, 2);
add_action('created_companion_category', 'hive_term_reindex_ping', 10, 2);
function hive_term_reindex_ping($term_id) {
    $link = get_term_link((int) $term_id, 'companion_category');
    if (!is_wp_error($link)) {
        hive_indexnow_ping_urls(array($link, home_url('/sitemap_index.xml')));
    }
}
