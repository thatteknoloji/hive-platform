<?php
/**
 * Mahalle → cadde/sokak → hizmet varyantı ağacı
 *
 * @package Hive_Ultra_Premium
 *
 * @var WP_Term $args['term']
 */

if (empty($args['term'])) {
    return;
}

$term = $args['term'];
$group = get_term_meta($term->term_id, 'hive_cat_group', true);
$children = hive_get_valid_categories(array(
    'parent'     => $term->term_id,
    'hide_empty' => false,
    'orderby'    => 'name',
    'order'      => 'ASC',
));

if (empty($children)) {
    return;
}

$locations = array();
$variants  = array();
$other     = array();

foreach ($children as $child) {
    $cg = get_term_meta($child->term_id, 'hive_cat_group', true);
    if ($cg === 'location') {
        $locations[] = $child;
    } elseif (in_array($cg, array('variant', 'variant_mahalle'), true)) {
        $variants[] = $child;
    } else {
        $other[] = $child;
    }
}

$render_group = function ($title, $items) {
    if (empty($items)) {
        return;
    }
    echo '<section class="category-child-group">';
    echo '<h2 class="category-child-group-title">' . esc_html($title) . '</h2>';
    echo '<div class="category-child-grid">';
    foreach ($items as $child) {
        $link = get_term_link($child);
        if (is_wp_error($link)) {
            continue;
        }
        $label = $child->name;
        if (function_exists('hive_category_menu_label')) {
            $label = hive_category_menu_label($child);
        }
        echo '<a class="category-child-card" href="' . esc_url($link) . '">';
        echo '<span class="category-child-name">' . esc_html($label) . '</span>';
        if ($child->count > 0) {
            echo '<span class="category-child-count">' . esc_html($child->count) . ' ' . esc_html__('ilan', 'hive-ultra-premium') . '</span>';
        }
        echo '</a>';
    }
    echo '</div></section>';
};
?>

<div class="category-tree-children">
    <p class="category-tree-parent-label">
        <?php
        printf(
            esc_html__('%s — alt kategoriler', 'hive-ultra-premium'),
            esc_html($term->name)
        );
        ?>
    </p>
    <?php
    if ($group === 'mahalle') {
        $render_group(__('Caddeler & Sokaklar', 'hive-ultra-premium'), $locations);
        $render_group(__('Mahalle Hizmet Varyantları', 'hive-ultra-premium'), $variants);
        $render_group(__('Diğer', 'hive-ultra-premium'), $other);
    } elseif ($group === 'location') {
        $render_group(__('Hizmet & Escort Varyantları', 'hive-ultra-premium'), $variants);
        $render_group(__('Diğer', 'hive-ultra-premium'), array_merge($locations, $other));
    } else {
        $render_group(__('Alt Kategoriler', 'hive-ultra-premium'), $children);
    }
    ?>
</div>
