<?php
/**
 * Main template fallback
 *
 * @package Hive_Ultra_Premium
 */

get_header();
?>

<main id="main-content" class="site-main">
    <div class="container">
        <header class="section-header">
            <h1><?php esc_html_e('Son Profiller', 'hive-ultra-premium'); ?></h1>
        </header>

        <?php
        $profiles = new WP_Query(array(
            'post_type'      => 'companion_profile',
            'posts_per_page' => 12,
            'paged'          => get_query_var('paged') ? get_query_var('paged') : 1,
        ));

        if ($profiles->have_posts()) :
            get_template_part('template-parts/slide', 'section', array(
                'title' => __('Öne Çıkan Profiller', 'hive-ultra-premium'),
                'query' => $profiles,
            ));

            echo '<div class="pagination">';
            echo paginate_links(array(
                'total'   => $profiles->max_num_pages,
                'current' => max(1, get_query_var('paged')),
            ));
            echo '</div>';
        else :
            ?>
            <div class="no-results">
                <p><?php esc_html_e('Henüz profil eklenmemiş.', 'hive-ultra-premium'); ?></p>
            </div>
            <?php
        endif;
        wp_reset_postdata();
        ?>
    </div>
</main>

<?php get_footer(); ?>
