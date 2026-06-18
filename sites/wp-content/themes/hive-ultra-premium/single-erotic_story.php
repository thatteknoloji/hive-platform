<?php
/**
 * Single erotic story template
 *
 * @package Hive_Ultra_Premium
 */

get_header();

while (have_posts()) :
    the_post();
    $sid      = get_the_ID();
    $lokasyon = get_post_meta($sid, 'story_lokasyon', true);
    $terms    = get_the_terms($sid, 'story_category');
    $cat_name = ($terms && !is_wp_error($terms)) ? $terms[0]->name : '';
    $cat_id   = ($terms && !is_wp_error($terms)) ? $terms[0]->term_id : 0;
    ?>

<main id="main-content" class="site-main">
    <div class="container">
        <?php if (function_exists('hive_breadcrumb')) {
            hive_breadcrumb();
        } ?>

        <article <?php post_class('erotic-story-single'); ?>>
            <header class="erotic-story-header">
                <?php if ($cat_name) : ?>
                    <span class="erotic-story-cat"><?php echo esc_html($cat_name); ?></span>
                <?php endif; ?>
                <h1><?php the_title(); ?></h1>
                <?php if ($lokasyon) : ?>
                    <p class="erotic-story-loc">📍 <?php echo esc_html($lokasyon); ?></p>
                <?php endif; ?>
                <div class="erotic-story-meta">
                    <?php hive_render_story_like_button($sid); ?>
                    <span class="erotic-story-date"><?php echo esc_html(get_the_date()); ?></span>
                </div>
            </header>

            <?php if (has_post_thumbnail()) : ?>
                <div class="erotic-story-featured">
                    <?php the_post_thumbnail('large', array('loading' => 'eager')); ?>
                </div>
            <?php endif; ?>

            <div class="erotic-story-content entry-content">
                <?php the_content(); ?>
            </div>

            <?php
            if ($lokasyon && function_exists('hive_render_map_iframe')) {
                echo '<section class="erotic-story-map">';
                echo '<h3>📍 ' . esc_html($lokasyon) . '</h3>';
                $map_addr = (stripos($lokasyon, 'kuşadası') !== false) ? $lokasyon : 'Kuşadası ' . $lokasyon;
                hive_render_map_iframe($map_addr, 14, 300);
                echo '</section>';
            }
            ?>

            <?php comments_template(); ?>
        </article>

        <?php
        /* Benzer hikayeler */
        if ($cat_id) {
            $similar_stories = new WP_Query(array(
                'post_type'      => 'erotic_story',
                'posts_per_page' => 6,
                'post__not_in'   => array($sid),
                'orderby'        => 'rand',
                'tax_query'      => array(
                    array('taxonomy' => 'story_category', 'field' => 'term_id', 'terms' => $cat_id),
                ),
            ));
            if ($similar_stories->have_posts()) :
                ?>
                <section class="erotic-story-related">
                    <h2><?php esc_html_e('Benzer Hikayeler', 'hive-ultra-premium'); ?></h2>
                    <div class="erotic-story-grid">
                        <?php
                        while ($similar_stories->have_posts()) :
                            $similar_stories->the_post();
                            get_template_part('template-parts/erotic-story', 'card');
                        endwhile;
                        ?>
                    </div>
                </section>
                <?php
            endif;
            wp_reset_postdata();
        }

        /* İlgili escort profilleri */
        $profiles = new WP_Query(array(
            'post_type'      => 'companion_profile',
            'posts_per_page' => 6,
            'orderby'        => 'rand',
        ));
        if ($profiles->have_posts()) :
            ?>
            <section class="erotic-story-profiles">
                <?php
                get_template_part('template-parts/slide', 'section', array(
                    'title' => '💋 ' . __('İlgili Escort Profilleri', 'hive-ultra-premium'),
                    'query' => $profiles,
                ));
                ?>
            </section>
            <?php
        endif;
        wp_reset_postdata();
        ?>
    </div>
</main>

    <?php
endwhile;

get_footer();
