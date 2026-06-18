<?php
/**
 * Page template
 *
 * @package Hive_Ultra_Premium
 */

get_header();
?>

<main id="main-content" class="site-main">
    <div class="container">
        <?php while (have_posts()) : the_post(); ?>
            <article <?php post_class('page-content'); ?>>
                <header class="section-header">
                    <h1><?php the_title(); ?></h1>
                </header>
                <div class="entry-content">
                    <?php the_content(); ?>
                </div>
            </article>
        <?php endwhile; ?>
    </div>
</main>

<?php get_footer(); ?>
