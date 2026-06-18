<?php
/**
 * Gömülü SEO içerik – sayfa altı, kapalı başlar
 *
 * @package Hive_Ultra_Premium
 *
 * @var string $args['title']
 * @var string $args['content']
 */

if (empty($args['content'])) {
    return;
}

$title   = isset($args['title']) ? $args['title'] : '';
$content = $args['content'];
?>
<section class="hive-seo-footer" aria-label="<?php echo esc_attr($title); ?>">
    <details class="hive-seo-footer-details">
        <summary class="hive-seo-footer-summary">
            <span class="hive-seo-footer-summary-text"><?php echo esc_html($title); ?></span>
            <span class="hive-seo-footer-hint"><?php esc_html_e('Rehberi genişlet', 'hive-ultra-premium'); ?></span>
        </summary>
        <div class="hive-seo-footer-body entry-content">
            <?php echo wp_kses_post($content); ?>
        </div>
    </details>
</section>
