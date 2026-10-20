# Output schema

schema_version 2. Generated from a real run. Every CSV has a header row; booleans are True/False; blanks are NaN.

`manifest.json` is the entry point: files (with row counts), config used, validation, warnings, league summaries and `recap_scopes`.

## data

Cleaned base tables (one row per song / vote / ballot / round). Join on league, round, song_idx.

| File | Rows | Columns |
|---|---|---|
| `data/songs.csv` | 816 | song, artist, genre, submitter, round_label, points, n_voters, league_label, league, round, uri, subgenre, major_genre, round_name, song_idx, raw_points, raw_voters, elig, submitter_voted, place, round_size, round_pct, status, cap, cap_known, budget, norm |
| `data/votes.csv` | 5288 | league, round, voter, uri, points, song_idx, song_submitter |
| `data/ballots.csv` | 730 | league, round, voter, n_votes, points |
| `data/rounds.csv` | 58 | league, round, round_name, league_label, songs, scored, forfeited, submitters, description, budget, songs_per_person, cap_input, ballots, cap, cap_known, league_complete |
| `data/participants.csv` | 24 | name |
| `data/validation.csv` | 21 | check, value, expected, status, detail |

## recap

Year recap. `recap/index.json` lists scopes. Each scope folder (`all`, `league_N`, `period_<name>`, `custom`) has `awards.json` (winners, headline, notes, thresholds, file list) and one CSV per award table. Folder `all` is shown; others have the same files.

| File | Rows | Columns |
|---|---|---|
| `recap/all/award_overall_champion.csv` | 24 | rank, player, total_points, submissions, round_wins, podiums, avg_place, raw_vote_points, forfeited_songs, avg_points_per_submission, normalized_sum |
| `recap/all/award_highest_scoring_song.csv` | 10 | rank, league, round, round_name, song, artist, submitter, total_points, supporters, elig, norm, status, share_of_available_points, supporters_pct |
| `recap/all/award_highest_scoring_song__by_share.csv` | 10 | rank, league, round, round_name, song, artist, submitter, total_points, supporters, elig, norm, status, share_of_available_points, supporters_pct |
| `recap/all/award_one_hit_wonder.csv` | 15 | rank, player, submissions, round_wins, best_song, best_round, best_points, best_normalized, other_avg_points, other_avg_normalized, one_hit_gap, one_hit_ratio, one_hit_index, best_vs_league_median_normalized, others_avg_round_percentile, best_supporters, best_supporters_pct |
| `recap/all/award_one_hit_wonder__ineligible.csv` | 1 | player, performance_submissions, minimum |
| `recap/all/award_consistency.csv` | 23 | rank, player, submissions_counted, avg_points, avg_normalized, sd_normalized, consistency_score |
| `recap/all/award_consistency__ineligible.csv` | 1 | player, submissions_counted, minimum |
| `recap/all/award_vote_spread.csv` | 38 | scope, point_value, votes, pct |
| `recap/all/award_genre_breakdown.csv` | 16 | major_genre, submissions, round_winning, submission_share, avg_normalized_score, genre_win_rate |
| `recap/all/award_genre_breakdown__player_fingerprint.csv` | 321 | player, major_genre, submission_genre_share, voting_genre_share, gap |
| `recap/all/award_you_know_who.csv` | 23 | rank, player, submissions, top_genre, top_genre_count, concentration |
| `recap/all/award_you_know_who__by_count.csv` | 23 | rank, player, submissions, top_genre, top_genre_count, concentration |
| `recap/all/award_you_know_who__ineligible.csv` | 1 | player, submissions, minimum |
| `recap/all/award_genre_explorer.csv` | 23 | rank, player, distinct_major_genres, submissions, evenness, genres |
| `recap/all/award_genre_explorer__ineligible.csv` | 1 | player, submissions, minimum |
| `recap/all/award_podium_throne.csv` | 23 | rank, player, submissions, gold, silver, bronze, podiums, weighted_score |
| `recap/all/award_podium_throne__ineligible.csv` | 1 | player, submissions, minimum |
| `recap/all/award_blowout_squeaker.csv` | 47 | rank, league, round, round_name, winning_song, artist, submitter, first_points, second_points, margin, margin_pct, eligible_voters |
| `recap/all/award_blowout_squeaker__squeaker_ranked.csv` | 47 | rank, league, round, round_name, winning_song, artist, submitter, first_points, second_points, margin, margin_pct, eligible_voters |
| `recap/all/award_blowout_squeaker__tied_first_place_rounds.csv` | 9 | league, round, round_name, winning_song, artist, submitter, first_points, second_points, margin, margin_pct, eligible_voters, official_winner, tied_score, tied_songs |
| `recap/all/award_generosity.csv` | 23 | rank, player, ballots, avg_support_breadth, avg_songs_supported, avg_top_song_share, ballots_in_unusual_budget_rounds |
| `recap/all/award_generosity__guest_list_order.csv` | 23 | rank, player, ballots, avg_support_breadth, avg_songs_supported, avg_top_song_share, ballots_in_unusual_budget_rounds |
| `recap/all/award_generosity__all_in_order.csv` | 23 | rank, player, ballots, avg_support_breadth, avg_songs_supported, avg_top_song_share, ballots_in_unusual_budget_rounds |
| `recap/all/award_generosity__ballot_level.csv` | 730 | player, league, round, supported, eligible_songs, breadth, top_song_share, unusual_budget |
| `recap/all/award_generosity__ineligible.csv` | 1 | player, ballots, minimum |
| `recap/all/award_times_gave_3plus.csv` | 24 | rank, player, positive_votes, high_votes_given, unique_songs_high, unique_submitters_high, high_vote_pct |
| `recap/all/award_times_gave_3plus__by_rate.csv` | 24 | rank, player, positive_votes, high_votes_given, unique_songs_high, unique_submitters_high, high_vote_pct |
| `recap/all/award_times_received_3plus.csv` | 24 | rank, player, submissions, high_votes_received, submissions_with_high_vote, unique_high_voters, high_votes_per_submission |
| `recap/all/award_times_received_3plus__by_rate.csv` | 24 | rank, player, submissions, high_votes_received, submissions_with_high_vote, unique_high_voters, high_votes_per_submission |
| `recap/all/award_title_cloud.csv` | 10 | scope, word, count |
| `recap/all/award_title_cloud__all_scopes.csv` | 803 | scope, word, count |
| `recap/all/award_biggest_fan.csv` | 23 | submitter, biggest_fan, tie, points_given, support_rate, shared_eligible_rounds, favorite_submission |
| `recap/all/award_biggest_fan__all_pairs.csv` | 444 | submitter, voter, points_given, shared_eligible_rounds, max_possible, support_rate, favorite_submission |

## league_N (one folder per league; League 1 shown)

Per-league analysis tables. `summary.json` has headline facts. Optional `profile_narratives.json` ({person: text}) is read by the dashboard.

| File | Rows | Columns |
|---|---|---|
| `league_1/round_results.csv` | 25 | league, round, round_name, place, song, artist, submitter, points, n_voters, status |
| `league_1/leaderboard.csv` | 12 | rank, submitter, submissions, official_points, wins, podiums, forfeited_songs, raw_vote_points, avg_points_per_submission, points_lost_to_forfeits |
| `league_1/songs.csv` | 85 | league, round, round_name, song, artist, submitter, genre, major_genre, subgenre, place, points, n_voters, raw_points, raw_voters, elig, avg_points_positive_voters, avg_points_eligible, share_eligible_voting, norm, round_pct, round_size, status, uri |
| `league_1/top_songs_total_points.csv` | 5 | rank, league, round, round_name, song, artist, submitter, genre, major_genre, subgenre, place, points, n_voters, raw_points, raw_voters, elig, avg_points_positive_voters, avg_points_eligible, share_eligible_voting, norm, round_pct, round_size, status, uri |
| `league_1/top_songs_avg_per_eligible_voter.csv` | 5 | rank, league, round, round_name, song, artist, submitter, genre, major_genre, subgenre, place, points, n_voters, raw_points, raw_voters, elig, avg_points_positive_voters, avg_points_eligible, share_eligible_voting, norm, round_pct, round_size, status, uri |
| `league_1/fans.csv` | 12 | submitter, biggest_fan, tie, fan_points, songs_scored_by_fan, avg_points_per_scored_song, share_of_received, total_received, forfeited_songs |
| `league_1/fan_pairs.csv` | 122 | submitter, voter, points, songs_scored |
| `league_1/fan_matrix.csv` | 12 | voter, Anya, Collin, Kelsey, Kristen, Leah, Logan, Maryann, Matt, Merita, Nicole, Olivia, Stephanie |
| `league_1/twins.csv` | 12 | voter, twin, tie, twin_combined, twin_cosine, twin_jaccard, shared_rounds, shared_songs, runner_up, runner_up_combined, margin_to_runner_up, near_tie, confidence, shared_positive_songs, top_shared_songs, note |
| `league_1/twin_pairs.csv` | 132 | voter, other, shared_rounds, shared_songs, cosine, jaccard, combined, status |
| `league_1/gems.csv` | 5 | rank, league, round, round_name, song, artist, submitter, genre, major_genre, subgenre, place, points, n_voters, raw_points, raw_voters, elig, avg_points_positive_voters, avg_points_eligible, share_eligible_voting, norm, round_pct, round_size, status, uri, breadth, breadth_pctile, bad_finish_pctile, gem_score, in_top_at_alt_weights |
| `league_1/gems_ranked.csv` | 43 | rank, league, round, round_name, song, artist, submitter, genre, major_genre, subgenre, place, points, n_voters, raw_points, raw_voters, elig, avg_points_positive_voters, avg_points_eligible, share_eligible_voting, norm, round_pct, round_size, status, uri, breadth, breadth_pctile, bad_finish_pctile, gem_score |
| `league_1/gems_excluded_forfeit.csv` | 1 | league, round, round_name, song, artist, submitter, genre, major_genre, subgenre, place, points, n_voters, raw_points, raw_voters, elig, avg_points_positive_voters, avg_points_eligible, share_eligible_voting, norm, round_pct, round_size, status, uri, breadth |
| `league_1/genre_summary.csv` | 24 | dimension, label, songs, distinct_submitters, total_official_points, share_of_songs, avg_points_per_scored_song, avg_normalized_score, popularity_rank, top_n |
| `league_1/profile_submissions.csv` | 85 | league, submitter, round, round_name, song, artist, genre, major_genre, subgenre, place, points, status |
| `league_1/profile_top_votes.csv` | 110 | person, song, artist, submitter, points_given, round_name |
| `league_1/profile_support.csv` | 860 | person, dimension, label, points_given, share |
| `league_1/profile_mix.csv` | 251 | person, dimension, label, submitted_share, rewarded_share, difference |
| `league_1/profile_summary.csv` | 12 | person, submissions, ballots, points_given, missing_rounds, top2_major_genre_share, major_genres_supported, most_supported_submitter, biggest_fan, taste_twin |
| `league_1/qc.csv` | 5 | check, value, expected, status |

