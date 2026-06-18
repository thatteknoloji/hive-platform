<?php
/**
 * Kategorize hamburger menü — escort tipleri + mahalleler
 *
 * @package Hive_Ultra_Premium
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Menü grupları (slug listeleri)
 *
 * @return array<int, array<string, mixed>>
 */
function hive_category_menu_groups() {
    return array(
        array(
            'id'    => 'uyruk',
            'label' => __('Uyruk & Yabancı', 'hive-ultra-premium'),
            'icon'  => '🌍',
            'slugs' => array(
                'turk-escort', 'rus-escort', 'ukraynali-escort', 'moldovali-escort', 'yabanci-escort',
                'beyaz-rus-escort', 'gurcu-escort', 'romen-escort', 'bulgar-escort', 'kazak-escort',
            ),
        ),
        array(
            'id'    => 'dil',
            'label' => __('Dil', 'hive-ultra-premium'),
            'icon'  => '💬',
            'slugs' => array(
                'ingilizce-escort', 'rusca-escort', 'almanca-escort', 'arapca-escort', 'fransizca-escort',
            ),
        ),
        array(
            'id'    => 'vip',
            'label' => __('VIP & Segment', 'hive-ultra-premium'),
            'icon'  => '⭐',
            'slugs' => array(
                'vip-escort', 'premium-escort', 'luks-escort', 'luxury-escort', 'elite-escort',
                'ucuz-escort', 'vip-model', 'premium-model', 'kusadasi-escort', 'aydin-escort', 'ege-escort',
            ),
        ),
        array(
            'id'    => 'yas',
            'label' => __('Yaş', 'hive-ultra-premium'),
            'icon'  => '👤',
            'slugs' => array(
                'genc-escort', 'yetiskin-escort', 'olgun-escort', 'orta-yas-escort',
            ),
        ),
        array(
            'id'    => 'gorunum',
            'label' => __('Görünüm', 'hive-ultra-premium'),
            'icon'  => '✨',
            'slugs' => array(
                'sarisin-escort', 'esmer-escort', 'kizil-escort', 'kumral-escort', 'uzun-boylu-escort',
                'minyon-escort', 'dolgun-escort', 'fit-escort', 'zayif-escort',
            ),
        ),
        array(
            'id'    => 'hizmet',
            'label' => __('Hizmet & Mekan', 'hive-ultra-premium'),
            'icon'  => '🏨',
            'slugs' => array(
                'anal-escort', 'oral-escort', 'cim-escort', 'cif-escort', 'cim-cif-escort',
                'deepthroat-escort', 'rimming-escort', 'french-kiss-escort', '69-escort',
                'masaj-escort', 'erotik-masaj-escort', 'nuru-masaj-escort', 'happy-ending-escort',
                'striptiz-escort', 'fantezi-escort', 'roleplay-escort', 'bdsm-escort', 'domina-escort',
                'cift-escort', 'grup-escort', 'uclu-escort', 'gfe-escort', 'milf-escort',
                'otel-escort', 'plaj-escort', 'gece-escort', '24saat-escort',
                'eve-gelen-escort', 'otele-gelen-escort', 'jakuzili-escort',
                'fetish-escort', 'ayak-fetis-escort', 'strapon-escort',
            ),
        ),
        array(
            'id'   => 'porn_en',
            'label'=> __('Adult Kategoriler (EN)', 'hive-ultra-premium'),
            'icon' => '🔞',
            'type' => 'porn_en',
        ),
        array(
            'id'   => 'porn_tr',
            'label'=> __('Adult Kategoriler (TR)', 'hive-ultra-premium'),
            'icon' => '🔞',
            'type' => 'porn_tr',
        ),
        array(
            'id'   => 'mahalle',
            'label'=> __('Mahalleler', 'hive-ultra-premium'),
            'icon' => '📍',
            'type' => 'mahalle',
        ),
    );
}

/**
 * Pornhub tarzı EN/TR kategoriler
 */
function hive_get_porn_categories($group) {
    $terms = get_terms(array(
        'taxonomy'   => 'companion_category',
        'hide_empty' => false,
        'parent'     => 0,
        'number'     => 0,
        'orderby'    => 'name',
        'order'      => 'ASC',
    ));
    if (is_wp_error($terms) || empty($terms)) {
        return array();
    }
    return array_values(array_filter($terms, function ($t) use ($group) {
        return hive_is_valid_category_term($t) && get_term_meta($t->term_id, 'hive_cat_group', true) === $group;
    }));
}

/**
 * Kısa kategori etiketi
 */
function hive_category_menu_label($term) {
    $name = (string) $term->name;
    $name = preg_replace('/^Kuşadası\s+/u', '', $name);
    return $name ?: $term->name;
}

/**
 * Slug → term link satırı
 *
 * @return array{name: string, url: string, count: int}|null
 */
function hive_category_menu_item_from_slug($slug) {
    $term = get_term_by('slug', $slug, 'companion_category');
    if (!$term || is_wp_error($term) || !hive_is_valid_category_term($term)) {
        return null;
    }
    $link = get_term_link($term);
    if (is_wp_error($link)) {
        return null;
    }
    return array(
        'name'  => hive_category_menu_label($term),
        'url'   => $link,
        'count' => (int) $term->count,
        'slug'  => $term->slug,
    );
}

/**
 * Accordion menü paneli
 *
 * @param bool $as_page Tam sayfa modu (/kategoriler)
 */
function hive_render_category_menu_panel($as_page = false) {
    $groups = hive_category_menu_groups();
    $panel_class = $as_page ? 'hive-cat-panel hive-cat-panel-page' : 'hive-cat-panel';
    ?>
    <div class="<?php echo esc_attr($panel_class); ?>" data-hive-cat-panel>
        <?php if ($as_page) : ?>
            <header class="hive-cat-panel-page-header">
                <h1><?php esc_html_e('Kuşadası Escort Kategorileri', 'hive-ultra-premium'); ?></h1>
                <p><?php esc_html_e('Uyruk, hizmet, mahalle ve daha fazlası — gruplar halinde gezinin.', 'hive-ultra-premium'); ?></p>
            </header>
        <?php endif; ?>

        <?php $search_id = $as_page ? 'hive-cat-search-page' : 'hive-cat-search-drawer'; ?>
        <div class="hive-cat-search-wrap">
            <label class="screen-reader-text" for="<?php echo esc_attr($search_id); ?>"><?php esc_html_e('Kategori ara', 'hive-ultra-premium'); ?></label>
            <input type="search" id="<?php echo esc_attr($search_id); ?>" class="hive-cat-search" placeholder="<?php esc_attr_e('Kategori ara…', 'hive-ultra-premium'); ?>" autocomplete="off" />
        </div>

        <div class="hive-cat-quicklinks">
            <a href="<?php echo esc_url(get_post_type_archive_link('companion_profile')); ?>"><?php esc_html_e('Tüm Profiller', 'hive-ultra-premium'); ?></a>
            <a href="<?php echo esc_url(get_post_type_archive_link('erotic_story')); ?>"><?php esc_html_e('Hikayeler', 'hive-ultra-premium'); ?></a>
        </div>

        <div class="hive-cat-accordion" role="navigation" aria-label="<?php esc_attr_e('Kategori grupları', 'hive-ultra-premium'); ?>">
            <?php foreach ($groups as $index => $group) :
                $open = $as_page && $index === 0;
                $group_id = 'hive-cat-group-' . esc_attr($group['id']);
                ?>
                <section class="hive-cat-group<?php echo $open ? ' is-open' : ''; ?>" data-hive-cat-group>
                    <button type="button" class="hive-cat-group-toggle" aria-expanded="<?php echo $open ? 'true' : 'false'; ?>" aria-controls="<?php echo $group_id; ?>">
                        <span class="hive-cat-group-icon" aria-hidden="true"><?php echo esc_html($group['icon']); ?></span>
                        <span class="hive-cat-group-label"><?php echo esc_html($group['label']); ?></span>
                        <span class="hive-cat-group-chevron" aria-hidden="true"></span>
                    </button>
                    <div id="<?php echo $group_id; ?>" class="hive-cat-group-body"<?php echo $open ? '' : ' hidden'; ?>>
                        <?php if (!empty($group['type']) && $group['type'] === 'mahalle') :
                            $mahalleler = hive_get_mahalle_categories();
                            foreach ($mahalleler as $parent) :
                                $parent_link = get_term_link($parent);
                                if (is_wp_error($parent_link)) {
                                    continue;
                                }
                                $children = hive_get_valid_categories(array(
                                    'parent'  => $parent->term_id,
                                    'orderby' => 'name',
                                    'order'   => 'ASC',
                                ));
                                ?>
                                <div class="hive-cat-mahalle-block" data-hive-cat-item data-search="<?php echo esc_attr(strtolower($parent->name . ' ' . $parent->slug)); ?>">
                                    <a class="hive-cat-mahalle-parent" href="<?php echo esc_url($parent_link); ?>">
                                        <?php echo esc_html(hive_category_menu_label($parent)); ?>
                                    </a>
                                    <?php if (!empty($children)) : ?>
                                        <ul class="hive-cat-mahalle-children">
                                            <?php foreach ($children as $child) :
                                                $child_link = get_term_link($child);
                                                if (is_wp_error($child_link)) {
                                                    continue;
                                                }
                                                ?>
                                                <li data-hive-cat-item data-search="<?php echo esc_attr(strtolower($child->name . ' ' . $child->slug . ' ' . $parent->name)); ?>">
                                                    <a href="<?php echo esc_url($child_link); ?>">
                                                        <?php echo esc_html(hive_category_menu_label($child)); ?>
                                                        <?php if ($child->count > 0) : ?>
                                                            <span class="hive-cat-count"><?php echo (int) $child->count; ?></span>
                                                        <?php endif; ?>
                                                    </a>
                                                </li>
                                            <?php endforeach; ?>
                                        </ul>
                                    <?php endif; ?>
                                </div>
                            <?php endforeach;
                        elseif (!empty($group['type']) && in_array($group['type'], array('porn_en', 'porn_tr'), true)) :
                            $porn_terms = hive_get_porn_categories($group['type']);
                            ?>
                            <ul class="hive-cat-links hive-cat-links-porn">
                                <?php foreach ($porn_terms as $pt) :
                                    $plink = get_term_link($pt);
                                    if (is_wp_error($plink)) {
                                        continue;
                                    }
                                    $plabel = get_term_meta($pt->term_id, 'hive_porn_label', true) ?: hive_category_menu_label($pt);
                                    ?>
                                    <li data-hive-cat-item data-search="<?php echo esc_attr(strtolower($plabel . ' ' . $pt->slug . ' ' . $pt->name)); ?>">
                                        <a href="<?php echo esc_url($plink); ?>">
                                            <?php echo esc_html($plabel); ?>
                                            <?php if ($pt->count > 0) : ?>
                                                <span class="hive-cat-count"><?php echo (int) $pt->count; ?></span>
                                            <?php endif; ?>
                                        </a>
                                    </li>
                                <?php endforeach; ?>
                            </ul>
                        <?php
                        else :
                            ?>
                            <ul class="hive-cat-links">
                                <?php
                                foreach ((array) ($group['slugs'] ?? array()) as $slug) :
                                    $item = hive_category_menu_item_from_slug($slug);
                                    if (!$item) {
                                        continue;
                                    }
                                    ?>
                                    <li data-hive-cat-item data-search="<?php echo esc_attr(strtolower($item['name'] . ' ' . $item['slug'])); ?>">
                                        <a href="<?php echo esc_url($item['url']); ?>">
                                            <?php echo esc_html($item['name']); ?>
                                            <?php if ($item['count'] > 0) : ?>
                                                <span class="hive-cat-count"><?php echo (int) $item['count']; ?></span>
                                            <?php endif; ?>
                                        </a>
                                    </li>
                                <?php endforeach; ?>
                            </ul>
                        <?php endif; ?>
                    </div>
                </section>
            <?php endforeach; ?>
        </div>
    </div>
    <?php
}

/**
 * Hamburger drawer (header’dan açılır)
 */
function hive_render_category_drawer() {
    ?>
    <div class="hive-cat-drawer-backdrop" data-hive-cat-close hidden></div>
    <aside id="hive-cat-drawer" class="hive-cat-drawer" aria-hidden="true" aria-labelledby="hive-cat-drawer-title">
        <div class="hive-cat-drawer-header">
            <h2 id="hive-cat-drawer-title"><?php esc_html_e('Kategoriler', 'hive-ultra-premium'); ?></h2>
            <button type="button" class="hive-cat-drawer-close" data-hive-cat-close aria-label="<?php esc_attr_e('Kapat', 'hive-ultra-premium'); ?>">×</button>
        </div>
        <?php hive_render_category_menu_panel(false); ?>
    </aside>
    <?php
}

add_action('wp_footer', 'hive_render_category_drawer', 5);
