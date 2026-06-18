<?php
/**
 * Yatay vitrin kategori poster sırası (görsel + hover büyütme)
 *
 * @package Hive_Ultra_Premium
 */

$limit = isset($args['limit']) ? (int) $args['limit'] : 20;
$terms = hive_get_valid_categories(array('number' => $limit, 'hide_empty' => true));

if (empty($terms)) {
    $terms = hive_get_valid_categories(array('number' => $limit));
}

if (empty($terms)) {
    return;
}

$terms = array_slice($terms, 0, max(12, $limit));
?>

<section class="category-showcase category-showcase-row" aria-label="<?php esc_attr_e('Kategoriler', 'hive-ultra-premium'); ?>">
    <div class="section-header">
        <h2><?php esc_html_e('Kategorilere Göz At', 'hive-ultra-premium'); ?></h2>
        <p><?php esc_html_e('Üzerine gel – yatay vitrin önizleme', 'hive-ultra-premium'); ?></p>
    </div>
    <div class="category-poster-scroll" tabindex="0">
        <div class="category-poster-track">
            <?php foreach ($terms as $term) :
                $link = get_term_link($term);
                if (is_wp_error($link)) {
                    continue;
                }
                $img = hive_category_poster_url($term->term_id);
                $count = (int) $term->count;
                ?>
                <a class="category-poster" href="<?php echo esc_url($link); ?>">
                    <div class="category-poster-image">
                        <img src="<?php echo esc_url($img); ?>" alt="<?php echo esc_attr($term->name); ?>" loading="lazy" decoding="async" />
                        <span class="category-poster-overlay"></span>
                    </div>
                    <div class="category-poster-info">
                        <span class="category-poster-name"><?php echo esc_html($term->name); ?></span>
                        <?php if ($count > 0) : ?>
                            <span class="category-poster-count"><?php echo esc_html($count); ?> profil</span>
                        <?php endif; ?>
                    </div>
                </a>
            <?php endforeach; ?>
        </div>
    </div>
</section>
