<?php
/**
 * Template Name: Favorilerim
 *
 * @package Hive_Ultra_Premium
 */

get_header();
?>

<main id="main-content" class="site-main">
    <div class="container">
        <?php hive_ultra_breadcrumb(); ?>
        <header class="section-header">
            <h1>♥ <?php esc_html_e('Favorilerim', 'hive-ultra-premium'); ?></h1>
            <p class="archive-description"><?php esc_html_e('Beğendiğiniz profiller burada listelenir.', 'hive-ultra-premium'); ?></p>
        </header>
        <div id="hive-favorites-list" class="hive-filter-results">
            <div class="hive-skeleton-grid">
                <?php for ($i = 0; $i < 3; $i++) : ?>
                    <div class="hive-skeleton-card"></div>
                <?php endfor; ?>
            </div>
        </div>
    </div>
</main>

<?php get_footer(); ?>
