<?php
/**
 * Footer template
 *
 * @package Hive_Ultra_Premium
 */
?>

<footer class="site-footer" role="contentinfo">
    <div class="container">
        <?php if (is_active_sidebar('footer-1') || is_active_sidebar('footer-2') || is_active_sidebar('footer-3')) : ?>
            <div class="footer-widgets">
                <?php if (is_active_sidebar('footer-1')) : ?>
                    <div class="footer-widget-area">
                        <?php dynamic_sidebar('footer-1'); ?>
                    </div>
                <?php endif; ?>
                <?php if (is_active_sidebar('footer-2')) : ?>
                    <div class="footer-widget-area">
                        <?php dynamic_sidebar('footer-2'); ?>
                    </div>
                <?php endif; ?>
                <?php if (is_active_sidebar('footer-3')) : ?>
                    <div class="footer-widget-area">
                        <?php dynamic_sidebar('footer-3'); ?>
                    </div>
                <?php endif; ?>
            </div>
        <?php endif; ?>

        <div class="site-info">
            <?php
            if (function_exists('hive_render_main_site_footer_link')) {
                hive_render_main_site_footer_link();
            }
            ?>
            <div class="site-footer-brand">
                <img src="<?php echo esc_url(hive_brand_logo_url()); ?>" alt="<?php esc_attr_e('Bal Kutusu', 'hive-ultra-premium'); ?>" class="site-footer-logo" width="160" height="40" loading="lazy" decoding="async" />
            </div>
            <?php get_template_part('template-parts/footer', 'disclaimer'); ?>
        </div>
    </div>
</footer>

<?php wp_footer(); ?>
</body>
</html>
