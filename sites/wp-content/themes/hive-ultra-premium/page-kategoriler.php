<?php
/**
 * Kategoriler hub – gruplu accordion menü
 *
 * @package Hive_Ultra_Premium
 */

get_header();
?>

<main id="main-content" class="site-main site-main-categories">
    <div class="container container-narrow">
        <?php hive_render_category_menu_panel(true); ?>
    </div>
</main>

<?php get_footer(); ?>
