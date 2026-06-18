<?php
/**
 * Balkutusu Index Recovery — canonical, 301, noindex, iç link, sitemap filtre
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

/** Profil olarak bilinen ?story= slug'ları */
function hive_index_profile_story_slugs() {
    return array('luna', 'bella', 'aylin');
}

/**
 * Türkçe slug normalize — tekrar eden token temizliği
 */
function hive_normalize_seo_slug($text, $max_words = 9) {
    $text = remove_accents((string) $text);
    $text = strtolower($text);
    $text = preg_replace('/[^a-z0-9\s\-]/', '', $text);
    $text = preg_replace('/\s+/', '-', trim($text));
    $text = preg_replace('/-+/', '-', $text);
    $parts = array_values(array_filter(explode('-', $text)));
    $synonyms = array(
        'kusadas' => 'kusadasi',
        'escorts' => 'escort',
        'bayanlar' => 'bayan',
        'yorumlar' => 'yorumlari',
        'gece-hayat' => 'gece-hayati',
    );
    $cleaned = array();
    foreach ($parts as $part) {
        $norm = isset($synonyms[$part]) ? $synonyms[$part] : $part;
        if (!empty($cleaned) && end($cleaned) === $norm) {
            continue;
        }
        if (in_array($norm, $cleaned, true)) {
            continue;
        }
        $cleaned[] = $norm;
    }
    if (count(array_keys($cleaned, 'sss', true)) > 1) {
        $seen_sss = false;
        $cleaned = array_values(array_filter($cleaned, function ($p) use (&$seen_sss) {
            if ($p !== 'sss') {
                return true;
            }
            if ($seen_sss) {
                return false;
            }
            $seen_sss = true;
            return true;
        }));
    }
    $cleaned = array_slice($cleaned, 0, max(3, min((int) $max_words, 12)));
    $slug = implode('-', $cleaned);
    if (strlen($slug) > 80) {
        $slug = substr($slug, 0, 80);
        $slug = rtrim($slug, '-');
    }
    return $slug ?: 'sayfa';
}

/**
 * Temiz canonical URL üret
 */
function hive_index_canonical_url() {
    if (is_search() || is_404()) {
        return '';
    }
    $home = trailingslashit(home_url('/'));

    if (is_front_page()) {
        return $home;
    }

    if (is_singular('companion_profile')) {
        return trailingslashit(home_url('/profil/' . get_post_field('post_name', get_queried_object_id()) . '/'));
    }
    if (is_singular('erotic_story')) {
        return trailingslashit(home_url('/hikaye/' . get_post_field('post_name', get_queried_object_id()) . '/'));
    }
    if (is_singular('gece_hayati')) {
        return trailingslashit(home_url('/gece-hayati/' . get_post_field('post_name', get_queried_object_id()) . '/'));
    }
    if (is_tax('companion_category')) {
        $term = get_queried_object();
        if ($term && !is_wp_error($term)) {
            return trailingslashit(home_url('/kategori/' . $term->slug . '/'));
        }
    }
    if (is_tax('gece_mahalle')) {
        $term = get_queried_object();
        if ($term && !is_wp_error($term)) {
            return trailingslashit(home_url('/gece-mahalle/' . $term->slug . '/'));
        }
    }

    $path = wp_parse_url(get_permalink(), PHP_URL_PATH);
    if (!$path) {
        return get_permalink();
    }
    $path = hive_index_normalize_legacy_path($path);
    return trailingslashit(home_url(untrailingslashit($path)));
}

function hive_index_normalize_legacy_path($path) {
    $path = '/' . ltrim((string) $path, '/');
    $path = preg_replace('#^/profiller/#', '/profil/', $path);
    $path = preg_replace('#^/hikayeler/#', '/hikaye/', $path);
    $path = preg_replace('#^/profil-kategori/#', '/kategori/', $path);
    if (preg_match('#^/(.+)/?$#', trim($path, '/'), $m)) {
        $slug = hive_normalize_seo_slug($m[1]);
        $parts = explode('/', trim($path, '/'));
        if (count($parts) === 1) {
            return '/' . $slug . '/';
        }
    }
    return $path;
}

/**
 * ?story= ve legacy path 301
 */
add_action('template_redirect', 'hive_index_recovery_redirects', 1);
function hive_index_recovery_redirects() {
    if (is_admin()) {
        return;
    }

    $request_uri = isset($_SERVER['REQUEST_URI']) ? wp_unslash($_SERVER['REQUEST_URI']) : '';
    $parsed = wp_parse_url($request_uri);
    $path = isset($parsed['path']) ? $parsed['path'] : '/';
    $query = isset($parsed['query']) ? $parsed['query'] : '';

    if ($query && preg_match('/(?:^|&)story=([^&]+)/', $query, $m)) {
        $slug = sanitize_title(rawurldecode($m[1]));
        if (in_array($slug, hive_index_profile_story_slugs(), true)) {
            $target = trailingslashit(home_url('/profil/' . $slug . '/'));
        } else {
            $target = trailingslashit(home_url('/hikaye/' . $slug . '/'));
        }
        wp_safe_redirect($target, 301);
        exit;
    }

    if (preg_match('#^/profiller(?:/|$)#', $path)) {
        $new_path = preg_replace('#^/profiller#', '/profil', $path);
        wp_safe_redirect(home_url($new_path) . (isset($parsed['query']) && $parsed['query'] ? '?' . $parsed['query'] : ''), 301);
        exit;
    }
    if (preg_match('#^/hikayeler(?:/|$)#', $path)) {
        $new_path = preg_replace('#^/hikayeler#', '/hikaye', $path);
        wp_safe_redirect(home_url($new_path) . (isset($parsed['query']) && $parsed['query'] ? '?' . $parsed['query'] : ''), 301);
        exit;
    }
    if (preg_match('#^/profil-kategori(?:/|$)#', $path)) {
        $new_path = preg_replace('#^/profil-kategori#', '/kategori', $path);
        wp_safe_redirect(home_url($new_path), 301);
        exit;
    }
}

add_action('wp_head', 'hive_index_recovery_canonical', 1);
function hive_index_recovery_canonical() {
    $url = hive_index_canonical_url();
    if ($url) {
        echo '<link rel="canonical" href="' . esc_url($url) . '" />' . "\n";
    }
}

add_action('wp_head', 'hive_index_recovery_robots', 2);
function hive_index_recovery_robots() {
    if (is_search() || is_tag() || is_author()) {
        echo '<meta name="robots" content="noindex, follow" />' . "\n";
        return;
    }
    if (!empty($_GET['story']) || !empty($_GET['s']) || !empty($_GET['post_type'])) {
        echo '<meta name="robots" content="noindex, follow" />' . "\n";
        return;
    }
    if (is_tax('companion_category')) {
        $term = get_queried_object();
        if ($term && (int) $term->count < 1) {
            echo '<meta name="robots" content="noindex, follow" />' . "\n";
        }
    }
}

add_filter('wp_sitemaps_posts_query_args', 'hive_index_sitemap_exclude', 10, 2);
function hive_index_sitemap_exclude($args, $post_type) {
    $args['post_status'] = 'publish';
    if ($post_type === 'story') {
        $args['post__in'] = array(0);
    }
    return $args;
}

add_filter('wp_sitemaps_posts_entry', 'hive_index_sitemap_entry', 10, 3);
function hive_index_sitemap_entry($entry, $post, $post_type) {
    if (empty($entry['loc'])) {
        return $entry;
    }
    $slug = $post->post_name;
    if ($post_type === 'companion_profile') {
        $entry['loc'] = trailingslashit(home_url('/profil/' . $slug . '/'));
    } elseif ($post_type === 'erotic_story') {
        $entry['loc'] = trailingslashit(home_url('/hikaye/' . $slug . '/'));
    } elseif ($post_type === 'gece_hayati') {
        $entry['loc'] = trailingslashit(home_url('/gece-hayati/' . $slug . '/'));
    }
    if (!empty($post->post_modified_gmt)) {
        $entry['lastmod'] = gmdate('c', strtotime($post->post_modified_gmt));
    }
    return $entry;
}

add_filter('wp_sitemaps_taxonomies_entry', 'hive_index_sitemap_tax_entry', 10, 4);
function hive_index_sitemap_tax_entry($entry, $term, $taxonomy) {
    if ($taxonomy === 'companion_category') {
        $entry['loc'] = trailingslashit(home_url('/kategori/' . $term->slug . '/'));
    } elseif ($taxonomy === 'gece_mahalle') {
        $entry['loc'] = trailingslashit(home_url('/gece-mahalle/' . $term->slug . '/'));
    }
    if ((int) $term->count < 1) {
        return array();
    }
    return $entry;
}

/**
 * İç link bloğu — indexlenebilir sayfalarda min 5 link
 */
add_filter('the_content', 'hive_index_internal_links_block', 99);
function hive_index_internal_links_block($content) {
    if (!is_singular() || is_admin() || !in_the_loop() || !is_main_query()) {
        return $content;
    }
    if (strpos($content, 'hive-internal-links') !== false) {
        return $content;
    }

    $links = hive_index_collect_internal_links();
    if (count($links) < 5) {
        return $content;
    }

    $html = '<nav class="hive-internal-links" aria-label="' . esc_attr__('İlgili içerikler', 'hive-ultra-premium') . '">';
    $html .= '<h2 class="hive-internal-links-title">' . esc_html__('İlgili içerikler', 'hive-ultra-premium') . '</h2><ul>';
    foreach (array_slice($links, 0, 8) as $link) {
        $html .= '<li><a href="' . esc_url($link['url']) . '">' . esc_html($link['text']) . '</a></li>';
    }
    $html .= '</ul></nav>';
    return $content . $html;
}

function hive_index_collect_internal_links() {
    $links = array();
    $home = trailingslashit(home_url('/'));
    $links[] = array('text' => __('Kuşadası escort ana sayfa', 'hive-ultra-premium'), 'url' => $home);

    if (is_singular('companion_profile')) {
        $post_id = get_the_ID();
        $terms = get_the_terms($post_id, 'companion_category');
        if ($terms && !is_wp_error($terms)) {
            $t = $terms[0];
            $links[] = array(
                'text' => sprintf(__('%s kategorisi', 'hive-ultra-premium'), $t->name),
                'url' => trailingslashit(home_url('/kategori/' . $t->slug . '/')),
            );
        }
        $mahalle = get_post_meta($post_id, 'mahalle', true);
        if ($mahalle) {
            $mslug = hive_normalize_seo_slug($mahalle);
            $links[] = array(
                'text' => sprintf(__('%s mahalle rehberi', 'hive-ultra-premium'), $mahalle),
                'url' => trailingslashit(home_url('/gece-mahalle/' . $mslug . '/')),
            );
        }
        $similar = get_posts(array(
            'post_type' => 'companion_profile',
            'posts_per_page' => 3,
            'post__not_in' => array($post_id),
            'orderby' => 'rand',
        ));
        foreach ($similar as $p) {
            $links[] = array(
                'text' => sprintf(__('Benzer profil: %s', 'hive-ultra-premium'), get_the_title($p)),
                'url' => trailingslashit(home_url('/profil/' . $p->post_name . '/')),
            );
        }
    } elseif (is_singular('erotic_story')) {
        $post_id = get_the_ID();
        $terms = get_the_terms($post_id, 'story_category');
        if ($terms && !is_wp_error($terms)) {
            $t = $terms[0];
            $links[] = array(
                'text' => sprintf(__('%s hikaye kategorisi', 'hive-ultra-premium'), $t->name),
                'url' => get_term_link($t),
            );
        }
        $stories = get_posts(array(
            'post_type' => 'erotic_story',
            'posts_per_page' => 3,
            'post__not_in' => array($post_id),
            'orderby' => 'rand',
        ));
        foreach ($stories as $p) {
            $links[] = array(
                'text' => get_the_title($p),
                'url' => trailingslashit(home_url('/hikaye/' . $p->post_name . '/')),
            );
        }
        $links[] = array(
            'text' => __('Kuşadası escort profilleri', 'hive-ultra-premium'),
            'url' => trailingslashit(home_url('/profil/')),
        );
    } else {
        $links[] = array('text' => __('Escort profilleri', 'hive-ultra-premium'), 'url' => trailingslashit(home_url('/profil/')));
        $links[] = array('text' => __('Hikayeler', 'hive-ultra-premium'), 'url' => trailingslashit(home_url('/hikaye/')));
        $links[] = array('text' => __('Gece hayatı rehberi', 'hive-ultra-premium'), 'url' => trailingslashit(home_url('/gece-hayati/')));
        $cats = get_terms(array('taxonomy' => 'companion_category', 'number' => 2, 'hide_empty' => true));
        if ($cats && !is_wp_error($cats)) {
            foreach ($cats as $c) {
                $links[] = array(
                    'text' => $c->name,
                    'url' => trailingslashit(home_url('/kategori/' . $c->slug . '/')),
                );
            }
        }
    }

    $links[] = array(
        'text' => __('Kuşadası gece rehberi', 'hive-ultra-premium'),
        'url' => trailingslashit(home_url('/rehber/')),
    );

    $seen = array();
    $uniq = array();
    foreach ($links as $l) {
        $u = rtrim($l['url'], '/');
        if (isset($seen[$u])) {
            continue;
        }
        $seen[$u] = true;
        $uniq[] = $l;
    }
    return $uniq;
}

add_filter('sanitize_title', 'hive_index_sanitize_title_slug', 20, 3);
function hive_index_sanitize_title_slug($title, $raw_title, $context) {
    if ($context !== 'save') {
        return $title;
    }
    return hive_normalize_seo_slug($title);
}

add_action('wp_head', 'hive_index_breadcrumb_schema', 5);
function hive_index_breadcrumb_schema() {
    if (is_front_page()) {
        return;
    }
    $items = array(
        array('@type' => 'ListItem', 'position' => 1, 'name' => 'Ana Sayfa', 'item' => home_url('/')),
    );
    $pos = 2;
    if (is_singular('companion_profile')) {
        $items[] = array('@type' => 'ListItem', 'position' => $pos++, 'name' => 'Profiller', 'item' => home_url('/profil/'));
        $items[] = array('@type' => 'ListItem', 'position' => $pos, 'name' => get_the_title(), 'item' => hive_index_canonical_url());
    } elseif (is_singular('erotic_story')) {
        $items[] = array('@type' => 'ListItem', 'position' => $pos++, 'name' => 'Hikayeler', 'item' => home_url('/hikaye/'));
        $items[] = array('@type' => 'ListItem', 'position' => $pos, 'name' => get_the_title(), 'item' => hive_index_canonical_url());
    } else {
        $items[] = array('@type' => 'ListItem', 'position' => $pos, 'name' => wp_get_document_title(), 'item' => hive_index_canonical_url());
    }
    $schema = array(
        '@context' => 'https://schema.org',
        '@type' => 'BreadcrumbList',
        'itemListElement' => $items,
    );
    echo '<script type="application/ld+json">' . wp_json_encode($schema, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . '</script>' . "\n";
}
