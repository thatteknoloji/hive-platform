<?php
/**
 * Birleşik profil arama formu
 *
 * @package Hive_Ultra_Premium
 */

$args = isset($args) && is_array($args) ? $args : array();
$id          = $args['id'] ?? 'hive-unified-search';
$placeholder = $args['placeholder'] ?? __('İlan adı, kullanıcı adı, kategori, lokasyon ara…', 'hive-ultra-premium');
$class       = $args['class'] ?? 'hive-unified-search';
$live        = !empty($args['live']);
$compact     = !empty($args['compact']);
$value       = get_search_query();
?>
<div class="<?php echo esc_attr($class); ?><?php echo $compact ? ' hive-unified-search--compact' : ''; ?>" data-hive-live-search="<?php echo $live ? '1' : '0'; ?>">
    <form role="search" method="get" class="hive-unified-search-form" action="<?php echo esc_url(home_url('/')); ?>">
        <label class="screen-reader-text" for="<?php echo esc_attr($id); ?>"><?php esc_html_e('Profil ara', 'hive-ultra-premium'); ?></label>
        <span class="hive-unified-search-icon" aria-hidden="true">🔍</span>
        <input
            type="search"
            id="<?php echo esc_attr($id); ?>"
            name="s"
            class="hive-unified-search-input"
            value="<?php echo esc_attr($value); ?>"
            placeholder="<?php echo esc_attr($placeholder); ?>"
            autocomplete="off"
            <?php echo $live ? 'data-hive-search-live="1"' : ''; ?>
        />
        <input type="hidden" name="post_type" value="companion_profile" />
        <button type="submit" class="btn btn-primary btn-small hive-unified-search-submit"><?php esc_html_e('Ara', 'hive-ultra-premium'); ?></button>
    </form>
    <?php if ($live) : ?>
        <div class="hive-unified-search-dropdown" hidden aria-live="polite"></div>
    <?php endif; ?>
</div>
