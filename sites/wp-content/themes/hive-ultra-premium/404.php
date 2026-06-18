<?php
/**
 * 404 template
 *
 * @package Hive_Ultra_Premium
 */

get_header();
?>

<main id="main-content" class="site-main">
    <div class="container">
        <section class="error-404">
            <h1>404</h1>
            <p><?php esc_html_e('Aradığınız sayfa bulunamadı.', 'hive-ultra-premium'); ?></p>
            <a href="<?php echo esc_url(home_url('/')); ?>" class="btn btn-primary">
                <?php esc_html_e('Ana Sayfaya Dön', 'hive-ultra-premium'); ?>
            </a>
        </section>
    </div>
</main>

<?php get_footer(); ?>
