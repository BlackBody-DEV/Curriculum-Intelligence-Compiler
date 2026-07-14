# ME 2301 Statics - Syllabus Curriculum Extraction

## Extraction Summary

- Subject: **Engineering Mechanics: Statics**
- Course: **ME 2301 Statics**
- Course-level skills: **9**
- Topics: **10**
- Subtopics: **50**
- Derived problem-solving microskills: **254**

> Topics and subtopics are explicit in the syllabus. Microskills are a granular problem-solving decomposition derived from the listed section scope. Repeated lecture entries were consolidated; summaries, exams, and administrative policy statements were excluded.

## Subject

- `subject_id`: `engineering_mechanics_statics`
- Subject name: **Engineering Mechanics: Statics**
- Course scope: particles, rigid bodies, trusses, frames, machines, forces, couples, internal loadings, friction, centroids, moments of inertia, and distributed loading.

## Course-Level Skills / Learning Outcomes

1. `analyze_particle_static_equilibrium` - Perform a static analysis of the forces acting on a particle.
2. `reduce_force_couple_system` - Reduce a system of forces and couples to a single equivalent force and couple.
3. `analyze_rigid_body_static_equilibrium` - Apply a static analysis to the forces and couples acting on a rigid body.
4. `analyze_trusses_frames_and_machines` - Perform a static analysis on trusses, frames, and machines.
5. `evaluate_internal_forces` - Evaluate the internal forces of a structural member.
6. `analyze_dry_friction` - Apply a static analysis to a rigid body subjected to dry friction.
7. `determine_centroids` - Determine the location of the centroid of areas and volumes.
8. `evaluate_area_moment_of_inertia` - Evaluate the moment of inertia of an area.
9. `analyze_distributed_loading` - Apply a static analysis to a rigid body subjected to a distributed load.

## Topic -> Subtopic -> Microskill Hierarchy

### 1. General Principles (`general_principles`)

**Topic skills**

- Model physical systems using statics idealizations.
- Use consistent dimensions, SI units, and numerical precision.
- Apply a systematic engineering problem-solving procedure.

#### 1-1 Mechanics (`mechanics`)

- `distinguish_statics_and_dynamics` - Distinguish statics from dynamics.
- `classify_mechanical_body_model` - Classify a body as a particle, rigid body, or deformable body.
- `identify_mechanics_problem_domain` - Identify whether a problem concerns forces, motion, or deformation.

#### 1-2 Fundamental Concepts (`fundamental_concepts`)

- `distinguish_mass_force_length_and_time` - Distinguish mass, force, length, and time as physical quantities.
- `apply_newtons_laws_to_static_systems` - Apply Newton's laws to systems in static equilibrium.
- `recognize_particle_and_rigid_body_idealizations` - Recognize when particle and rigid-body idealizations are valid.
- `distinguish_scalar_and_vector_quantities` - Distinguish scalar quantities from vector quantities.

#### 1-3 Units of Measurement (`units_of_measurement`)

- `track_physical_dimensions` - Track the physical dimensions of quantities.
- `convert_between_unit_systems` - Convert quantities between compatible unit systems.
- `verify_dimensional_homogeneity` - Verify that an equation is dimensionally homogeneous.
- `maintain_unit_consistency` - Maintain consistent units throughout a calculation.

#### 1-4 International System of Units (`international_system_of_units`)

- `use_si_base_and_derived_units` - Use SI base and derived units in statics calculations.
- `apply_si_prefixes` - Apply SI prefixes and powers of ten correctly.
- `distinguish_mass_and_weight` - Distinguish mass from weight.
- `calculate_weight_from_mass` - Calculate weight using W = mg with consistent units.

#### 1-5 Numerical Calculations (`numerical_calculations`)

- `use_scientific_notation` - Use scientific notation correctly.
- `retain_guard_digits` - Retain guard digits during intermediate calculations.
- `round_to_appropriate_significant_figures` - Round final results to appropriate significant figures.
- `report_value_with_units_and_sign` - Report numerical answers with correct units, magnitude, and sign.

#### 1-6 General Procedure for Analysis (`general_procedure_for_analysis`)

- `identify_knowns_unknowns_and_objective` - Identify known quantities, unknowns, and the requested result.
- `select_system_and_body_model` - Select the system boundary and appropriate body model.
- `state_assumptions_and_idealizations` - State assumptions and idealizations.
- `draw_solution_diagram_or_free_body_diagram` - Draw the required geometry diagram or free-body diagram.
- `select_governing_equations` - Select governing vector, moment, or equilibrium equations.
- `solve_equations_systematically` - Solve the equations in a logical sequence.
- `check_units_signs_and_reasonableness` - Check units, signs, equilibrium, and physical reasonableness.

### 2. Force Vectors (`force_vectors`)

**Topic skills**

- Represent forces as vectors in geometric and Cartesian form.
- Resolve, add, and project vectors in two and three dimensions.
- Construct force vectors from geometry and point coordinates.

#### 2-1 Scalars and Vectors (`scalars_and_vectors`)

- `identify_vector_magnitude_direction_and_sense` - Identify a vector's magnitude, direction, and sense.
- `represent_vector_graphically` - Represent a vector graphically with a directed line segment.
- `distinguish_vector_equality_and_negative_vectors` - Distinguish equal vectors and negative vectors.
- `use_vector_notation` - Use consistent vector and magnitude notation.

#### 2-2 Vector Operations (`vector_operations`)

- `multiply_vector_by_scalar` - Multiply or divide a vector by a scalar.
- `add_vectors_by_triangle_rule` - Add vectors using the triangle rule.
- `add_vectors_by_parallelogram_rule` - Add vectors using the parallelogram rule.
- `subtract_vectors` - Subtract vectors by adding the negative vector.
- `resolve_vector_into_components` - Resolve a vector into specified components.

#### 2-3 Vector Addition of Forces (`vector_addition_of_forces`)

- `construct_resultant_of_two_forces` - Construct the resultant of two concurrent forces.
- `calculate_resultant_with_law_of_cosines` - Calculate a force resultant using the law of cosines.
- `calculate_direction_with_law_of_sines` - Calculate a resultant direction using the law of sines.
- `resolve_force_along_oblique_axes` - Resolve a force along non-orthogonal directions.

#### 2-4 Addition of a Set of Coplanar Vectors (`addition_of_coplanar_vectors`)

- `resolve_coplanar_force_into_rectangular_components` - Resolve each coplanar force into rectangular components.
- `sum_coplanar_vector_components` - Sum x- and y-components of multiple vectors.
- `calculate_coplanar_resultant_magnitude` - Calculate the magnitude of a coplanar resultant.
- `calculate_coplanar_resultant_direction` - Calculate the direction and quadrant of a coplanar resultant.
- `determine_equilibrant_of_coplanar_force_set` - Determine the equilibrant of a coplanar force set.

#### 2-5 Cartesian Vectors (`cartesian_vectors`)

- `express_vector_with_cartesian_unit_vectors` - Express a vector using i, j, and k unit vectors.
- `calculate_vector_magnitude_from_components` - Calculate vector magnitude from Cartesian components.
- `calculate_coordinate_direction_angles` - Calculate coordinate direction angles.
- `use_direction_cosines` - Use direction cosines and their identity.
- `construct_cartesian_vector_from_magnitude_and_angles` - Construct a Cartesian vector from magnitude and direction angles.

#### 2-6 Addition of Cartesian Vectors (`addition_of_cartesian_vectors`)

- `add_cartesian_vectors_componentwise` - Add Cartesian vectors component by component.
- `subtract_cartesian_vectors_componentwise` - Subtract Cartesian vectors component by component.
- `calculate_3d_resultant_magnitude` - Calculate the magnitude of a three-dimensional resultant.
- `calculate_3d_resultant_direction_angles` - Calculate coordinate direction angles of a three-dimensional resultant.

#### 2-7 Position Vectors (`position_vectors`)

- `construct_position_vector_from_coordinates` - Construct a position vector from point coordinates.
- `construct_relative_position_vector` - Construct the vector from one point to another.
- `calculate_distance_between_points` - Calculate distance between two points from a position vector.
- `reverse_position_vector_direction` - Reverse a position vector and its sign correctly.

#### 2-8 Force Vector Directed Along a Line (`force_vector_directed_along_a_line`)

- `construct_line_of_action_unit_vector` - Construct a unit vector along a line defined by two points.
- `construct_force_vector_from_magnitude_and_line` - Construct a force vector from its magnitude and line of action.
- `extract_force_components_from_geometry` - Extract Cartesian force components from geometry.
- `determine_cable_force_direction` - Determine the correct direction of a cable or link force.

#### 2-9 Dot Product (`dot_product`)

- `calculate_vector_dot_product` - Calculate the dot product of two vectors.
- `calculate_angle_between_vectors` - Calculate the angle between two vectors.
- `calculate_scalar_projection_on_axis` - Calculate the scalar projection of a vector onto an axis.
- `calculate_vector_projection_on_axis` - Calculate the vector projection onto an axis.
- `test_vector_perpendicularity` - Test whether two vectors are perpendicular.

### 3. Equilibrium of a Particle (`particle_equilibrium`)

**Topic skills**

- Create particle free-body diagrams.
- Apply two- and three-dimensional particle equilibrium equations.
- Solve cable, spring, and concurrent-force equilibrium problems.

#### 3-1 Condition for the Equilibrium of a Particle (`condition_for_particle_equilibrium`)

- `state_particle_equilibrium_vector_equation` - State particle equilibrium as ΣF = 0.
- `translate_particle_equilibrium_to_scalar_equations` - Translate vector equilibrium into scalar component equations.
- `determine_whether_particle_is_in_equilibrium` - Determine whether a particle is in equilibrium.
- `solve_unknown_concurrent_forces` - Solve for unknown magnitudes or directions of concurrent forces.

#### 3-2 Free-Body Diagram of a Particle (`particle_free_body_diagram`)

- `isolate_particle_from_surroundings` - Isolate the particle from its surroundings.
- `identify_all_external_forces_on_particle` - Identify all external forces acting on the particle.
- `model_cable_tension_spring_and_contact_forces` - Model cable tension, spring force, weight, and smooth-contact forces.
- `label_force_directions_and_geometry` - Label force directions, angles, and geometry.
- `avoid_including_internal_or_nonacting_forces` - Exclude internal forces and forces not acting on the isolated particle.

#### 3-3 Coplanar Force Systems (`coplanar_particle_force_systems`)

- `resolve_particle_forces_into_xy_components` - Resolve all particle forces into x- and y-components.
- `write_particle_equilibrium_x_y` - Write ΣFx = 0 and ΣFy = 0.
- `solve_two_dimensional_particle_equilibrium` - Solve two-dimensional particle equilibrium equations.
- `determine_unknown_cable_tensions_2d` - Determine unknown cable tensions in planar systems.
- `check_force_direction_assumptions_2d` - Interpret negative solutions and check assumed force directions.

#### 3-4 Three-Dimensional Force Systems (`three_dimensional_particle_force_systems`)

- `draw_3d_particle_free_body_diagram` - Draw a three-dimensional particle free-body diagram.
- `express_3d_particle_forces_in_cartesian_form` - Express each force in Cartesian vector form.
- `write_particle_equilibrium_x_y_z` - Write ΣFx = 0, ΣFy = 0, and ΣFz = 0.
- `solve_three_dimensional_particle_equilibrium` - Solve for unknown three-dimensional force magnitudes.
- `determine_3d_cable_tensions_from_coordinates` - Determine cable tensions using point coordinates and unit vectors.

### 4. Force System Resultants (`force_system_resultants`)

**Topic skills**

- Calculate moments of forces and couples.
- Reduce force systems to equivalent resultants or force-couple systems.
- Replace distributed loadings with equivalent concentrated forces.

#### 4-1 Moment of a Force - Scalar Formulation (`moment_of_force_scalar`)

- `calculate_moment_as_force_times_perpendicular_distance` - Calculate moment magnitude using M = Fd⊥.
- `determine_clockwise_counterclockwise_moment_sign` - Assign clockwise or counterclockwise moment sign.
- `identify_force_line_of_action` - Identify a force's line of action and perpendicular distance.
- `select_moment_center_for_scalar_calculation` - Select a useful moment center for a scalar calculation.

#### 4-2 Cross Product (`cross_product`)

- `calculate_cross_product_with_determinant` - Calculate a cross product using determinant expansion.
- `apply_right_hand_rule_to_cross_product` - Determine cross-product direction with the right-hand rule.
- `calculate_cross_product_magnitude` - Calculate cross-product magnitude from vector magnitudes and angle.
- `respect_cross_product_order` - Apply the noncommutative order of the cross product.

#### 4-3 Moment of a Force - Vector Formulation (`moment_of_force_vector`)

- `construct_position_vector_to_force_line` - Construct a position vector from the moment point to any point on the force line.
- `calculate_moment_vector_r_cross_f` - Calculate a moment vector using M_O = r × F.
- `calculate_3d_moment_components` - Calculate x-, y-, and z-components of a moment.
- `verify_moment_vector_direction` - Verify moment direction using geometry or the right-hand rule.

#### 4-4 Principle of Moments (`principle_of_moments`)

- `apply_varignons_theorem` - Apply Varignon's theorem to decompose a force into components.
- `sum_moments_of_multiple_forces` - Sum moments of multiple forces about a point.
- `calculate_moment_of_resultant_force` - Calculate the moment of a resultant force.
- `choose_convenient_force_components_for_moment` - Choose convenient components to simplify moment calculations.

#### 4-5 Moment of a Force About a Specified Axis (`moment_about_specified_axis`)

- `construct_axis_unit_vector` - Construct a unit vector along the specified axis.
- `calculate_moment_about_axis_scalar` - Calculate moment about an axis using u_axis · (r × F).
- `determine_axis_moment_sign` - Determine the signed sense of moment about an axis.
- `select_position_vector_from_axis_to_force` - Select a valid position vector from the axis to the force line.

#### 4-6 Moment of a Couple (`moment_of_couple`)

- `identify_force_couple` - Identify two equal, opposite, noncollinear forces as a couple.
- `calculate_couple_moment` - Calculate the moment of a couple.
- `recognize_couple_as_free_vector` - Recognize that a couple moment is independent of reference point.
- `combine_multiple_couple_moments` - Combine multiple couple moments vectorially.
- `replace_couple_with_equivalent_couple` - Replace a couple with an equivalent couple of different force and arm.

#### 4-7 Simplification of a Force-Couple System (`force_couple_system_simplification`)

- `sum_forces_to_equivalent_resultant` - Sum all forces to obtain the equivalent resultant force.
- `sum_moments_about_reference_point` - Sum force moments and couples about a reference point.
- `move_force_to_new_point_with_added_couple` - Move a force to a new point by adding the required couple moment.
- `represent_system_as_resultant_force_and_couple` - Represent a general system as an equivalent force-couple system.

#### 4-8 Further Simplification of a Force and Couple System (`further_force_couple_simplification`)

- `classify_equivalent_system_as_force_couple_or_zero` - Classify the reduced system as a single force, pure couple, general force-couple, or zero.
- `reduce_coplanar_system_to_single_resultant` - Reduce a coplanar force system to a single resultant when possible.
- `locate_resultant_line_of_action` - Locate the resultant's line of action from the net moment.
- `determine_resultant_intercepts` - Determine where a resultant crosses a selected axis.
- `verify_equivalence_of_reduced_system` - Verify that the reduced system preserves force and moment effects.

#### 4-9 Reduction of a Simple Distributed Loading (`simple_distributed_loading`)

- `interpret_distributed_load_intensity` - Interpret distributed load intensity and units.
- `calculate_distributed_load_resultant_by_area` - Calculate resultant force as the area under the loading diagram.
- `locate_distributed_load_resultant_at_centroid` - Locate the resultant through the centroid of the loading diagram.
- `reduce_rectangular_triangular_and_trapezoidal_loads` - Reduce rectangular, triangular, and trapezoidal loadings.
- `integrate_variable_distributed_load` - Integrate a load function to determine resultant magnitude and location.
- `replace_distributed_load_on_free_body_diagram` - Replace a distributed load with its equivalent concentrated force on an FBD.

### 5. Equilibrium of a Rigid Body (`rigid_body_equilibrium`)

**Topic skills**

- Construct two- and three-dimensional rigid-body free-body diagrams.
- Apply force and moment equilibrium to solve support reactions.
- Evaluate constraints, determinacy, and special two- or three-force members.

#### 5-1 Conditions for Rigid-Body Equilibrium (`conditions_for_rigid_body_equilibrium`)

- `state_rigid_body_force_and_moment_equilibrium` - State rigid-body equilibrium as ΣF = 0 and ΣM = 0.
- `distinguish_translational_and_rotational_equilibrium` - Distinguish translational from rotational equilibrium.
- `write_planar_rigid_body_equilibrium_equations` - Write the three independent planar equilibrium equations.
- `state_spatial_rigid_body_equilibrium_components` - State the six scalar equilibrium equations for a spatial rigid body.

#### 5-2 Free-Body Diagrams - Two-Dimensional Rigid Bodies (`rigid_body_free_body_diagrams_2d`)

- `isolate_planar_rigid_body` - Isolate a planar rigid body from its surroundings.
- `model_pin_roller_cable_and_link_reactions` - Model pin, roller, cable, smooth-contact, and link reactions.
- `model_fixed_support_reactions_2d` - Model force components and reaction moment at a fixed support.
- `include_applied_couples_and_equivalent_distributed_loads` - Include applied couples and equivalent distributed-load resultants.
- `show_dimensions_and_force_application_points` - Show dimensions and force application points needed for moments.

#### 5-3 Equations of Equilibrium - Two Dimensions (`equations_of_equilibrium_2d`)

- `select_moment_center_to_eliminate_unknowns` - Select a moment center that eliminates unknown reactions.
- `solve_planar_support_reactions` - Solve planar support-reaction problems.
- `apply_alternative_planar_equilibrium_equation_sets` - Apply valid alternative sets of planar equilibrium equations.
- `interpret_negative_reaction_components` - Interpret negative reaction components as opposite assumed directions.
- `verify_planar_rigid_body_equilibrium` - Verify all force and moment equilibrium equations.

#### 5-4 Two- and Three-Force Members (`two_and_three_force_members`)

- `identify_two_force_member` - Identify a two-force member.
- `apply_collinearity_to_two_force_member` - Apply equal, opposite, and collinear end forces to a two-force member.
- `identify_three_force_member` - Identify a three-force member.
- `apply_concurrence_or_parallelism_to_three_force_member` - Apply concurrency or parallelism conditions to a three-force member.
- `infer_unknown_reaction_line_of_action` - Infer an unknown reaction's line of action from member geometry.

#### 5-5 Free-Body Diagrams - Three-Dimensional Rigid Bodies (`rigid_body_free_body_diagrams_3d`)

- `isolate_spatial_rigid_body` - Isolate a three-dimensional rigid body.
- `model_ball_socket_bearing_and_cable_reactions` - Model ball-and-socket, bearing, cable, and smooth-surface reactions.
- `determine_reaction_components_allowed_by_support` - Determine which force and couple components a spatial support can exert.
- `express_spatial_forces_and_moments_as_cartesian_vectors` - Express applied and reaction forces and moments as Cartesian vectors.
- `apply_spatial_rigid_body_equilibrium` - Apply ΣFx = ΣFy = ΣFz = 0 and ΣMx = ΣMy = ΣMz = 0.
- `solve_spatial_support_reactions` - Solve three-dimensional support-reaction problems.

#### 5-7 Constraints and Statical Determinacy (`constraints_and_statical_determinacy`)

- `count_independent_equilibrium_equations_and_unknowns` - Count independent equilibrium equations and reaction unknowns.
- `classify_statically_determinate_or_indeterminate_system` - Classify a support system as statically determinate or indeterminate.
- `identify_improper_constraints` - Identify redundant, parallel, concurrent, or otherwise improper constraints.
- `identify_unstable_rigid_body_support` - Identify support arrangements that permit rigid-body motion.
- `distinguish_external_and_internal_determinacy` - Distinguish external support determinacy from internal structural determinacy.

### 6. Structural Analysis (`structural_analysis`)

**Topic skills**

- Analyze simple trusses using joint and section equilibrium.
- Analyze frames and machines by separating interconnected members.
- Determine member forces and classify tension or compression.

#### 6-1 Simple Trusses (`simple_trusses`)

> The method of joints is required to perform the syllabus truss-analysis outcome, although section 6-2 is not separately listed in the schedule.

- `recognize_simple_planar_truss_assumptions` - Recognize ideal planar-truss assumptions: pin joints, two-force members, and joint loading.
- `identify_truss_members_joints_and_supports` - Identify members, joints, and support reactions.
- `calculate_truss_support_reactions` - Calculate external support reactions for the whole truss.
- `identify_zero_force_members` - Identify zero-force members by joint inspection.
- `apply_method_of_joints` - Apply joint equilibrium to solve member forces. [derived_implied_by_truss_outcome]
- `classify_truss_member_tension_or_compression` - Classify each solved member as tension or compression.
- `check_planar_truss_determinacy` - Check simple planar truss determinacy using member-joint-reaction counts.

#### 6-4 Method of Sections (`method_of_sections`)

- `select_truss_cut_with_limited_unknowns` - Select a cut passing through no more than three unknown member forces.
- `isolate_one_side_of_cut_truss` - Isolate the simpler side of the cut truss.
- `assume_cut_member_forces_in_tension` - Assume cut member forces act in tension away from the cut.
- `use_moments_to_solve_target_member_force` - Choose a moment center to solve a target member directly.
- `solve_remaining_cut_member_forces` - Use force equilibrium to solve remaining cut-member forces.
- `interpret_section_force_signs` - Interpret signs as tension or compression.

#### 6-6 Frames and Machines (`frames_and_machines`)

- `distinguish_frame_from_machine` - Distinguish a frame from a machine.
- `identify_multiforce_and_two_force_members` - Identify multi-force and two-force members in an assembly.
- `disassemble_structure_at_internal_pins` - Disassemble the assembly at internal pins and contacts.
- `draw_free_body_diagram_for_each_member` - Draw a separate free-body diagram for each required member.
- `apply_action_reaction_at_internal_connections` - Apply equal-and-opposite forces at internal connections.
- `solve_member_equilibrium_in_useful_sequence` - Solve member equilibrium equations in a useful sequence.
- `determine_internal_pin_and_contact_forces` - Determine internal pin, contact, and actuator forces.

### 7. Internal Forces (`internal_forces`)

**Topic skills**

- Determine internal normal force, shear force, bending moment, and torque at a cut.
- Relate distributed load, shear, and bending moment.
- Construct and interpret shear-force and bending-moment diagrams.

#### 7-1 Internal Loadings in Structural Members (`internal_loadings_in_structural_members`)

- `select_cut_location_in_structural_member` - Select a cut at the point where internal loading is required.
- `isolate_one_segment_after_cut` - Isolate the simpler segment of the cut member.
- `expose_internal_normal_shear_moment_and_torque` - Expose internal normal force, shear force, bending moment, and torque as applicable.
- `apply_internal_loading_sign_convention` - Apply a consistent internal-loading sign convention.
- `solve_internal_loadings_with_equilibrium` - Use equilibrium to solve internal loadings.
- `interpret_negative_internal_loading_result` - Interpret a negative result as opposite to the assumed internal-load direction.

#### 7-3 Relations Between Distributed Load, Shear, and Moment (`distributed_load_shear_moment_relations`)

- `apply_differential_load_shear_relation` - Apply the differential relation between load intensity and shear.
- `apply_differential_shear_moment_relation` - Apply the differential relation between shear and bending moment.
- `calculate_shear_change_from_load_area` - Calculate change in shear from area under the load diagram.
- `calculate_moment_change_from_shear_area` - Calculate change in moment from area under the shear diagram.
- `account_for_point_load_jumps_in_shear` - Account for shear jumps caused by concentrated forces.
- `account_for_applied_couple_jumps_in_moment` - Account for moment-diagram jumps caused by applied couples.
- `construct_shear_force_diagram` - Construct a shear-force diagram from loading and reactions.
- `construct_bending_moment_diagram` - Construct a bending-moment diagram from the shear diagram.
- `locate_bending_moment_extrema` - Locate bending-moment extrema where shear is zero or changes sign.
- `apply_beam_boundary_conditions` - Apply appropriate beam-end and support boundary conditions.

### 8. Dry Friction (`dry_friction`)

**Topic skills**

- Model static and kinetic dry-friction forces.
- Determine impending motion, sliding, tipping, and equilibrium.
- Analyze wedges and threaded screws with friction.

#### 8-1 Characteristics of Dry Friction (`characteristics_of_dry_friction`)

- `identify_friction_force_direction` - Identify friction direction as opposing actual or impending relative motion.
- `distinguish_static_and_kinetic_friction` - Distinguish static friction from kinetic friction.
- `apply_static_friction_inequality` - Apply 0 ≤ F_s ≤ μ_s N for non-impending equilibrium.
- `apply_limiting_static_friction` - Apply F_s = μ_s N at impending motion.
- `apply_kinetic_friction_law` - Apply F_k = μ_k N during sliding.
- `calculate_angle_of_friction` - Calculate and use the angle of friction.

#### 8-2 Problems Involving Dry Friction (`problems_involving_dry_friction`)

- `draw_frictional_contact_free_body_diagram` - Draw a free-body diagram with normal and friction forces at each contact.
- `predict_impending_motion_direction` - Predict the direction of impending motion.
- `select_equilibrium_or_impending_friction_model` - Select an inequality or limiting-friction model appropriate to the state.
- `solve_required_force_or_friction_coefficient` - Solve for an applied force, normal force, or friction coefficient.
- `check_no_slip_friction_requirement` - Check that the required friction does not exceed μ_s N.
- `compare_tipping_and_sliding_thresholds` - Compare tipping and sliding thresholds.
- `locate_normal_reaction_for_tipping` - Locate the normal reaction at the edge at impending tip.
- `verify_assumed_motion_and_friction_directions` - Verify assumed motion and friction directions after solving.

#### 8-3 Wedges (`wedges`)

- `separate_wedge_and_supported_body` - Separate the wedge and supported body into individual free bodies.
- `assign_friction_directions_at_wedge_contacts` - Assign friction directions at each wedge contact.
- `apply_equilibrium_to_wedge_system` - Apply equilibrium to the wedge and supported body.
- `calculate_force_to_raise_lower_or_hold_load_with_wedge` - Calculate force required to raise, lower, or hold a load with a wedge.
- `determine_wedge_self_locking_condition` - Determine whether a wedge is self-locking.

#### 8-4 Frictional Forces on Screws (`frictional_forces_on_screws`)

- `model_screw_thread_as_inclined_plane` - Model a screw thread as an unwrapped inclined plane.
- `calculate_screw_lead_angle` - Calculate screw lead angle from lead and mean radius.
- `calculate_torque_to_raise_load_with_screw` - Calculate torque required to raise a load.
- `calculate_torque_to_lower_load_with_screw` - Calculate torque required to lower a load.
- `determine_screw_self_locking_condition` - Determine whether a screw is self-locking.
- `evaluate_screw_mechanical_efficiency` - Evaluate screw mechanical efficiency when required.

### 9. Center of Gravity, Center of Mass, and Centroids (`centers_and_centroids`)

**Topic skills**

- Locate centers of gravity, centers of mass, and geometric centroids.
- Determine centroids of composite areas and volumes.
- Apply the theorems of Pappus and Guldinus.

#### 9-1 Center of Gravity, Center of Mass, and the Centroid of a Body (`center_of_gravity_center_of_mass_and_centroid`)

- `distinguish_center_of_gravity_mass_and_centroid` - Distinguish center of gravity, center of mass, and geometric centroid.
- `write_first_moment_centroid_equations` - Write first-moment equations for lines, areas, and volumes.
- `set_up_centroid_integral` - Set up centroid integrals using differential elements.
- `choose_differential_element_and_bounds` - Choose a useful differential element and integration bounds.
- `use_symmetry_to_locate_centroid_coordinates` - Use symmetry to locate one or more centroid coordinates.
- `calculate_centroid_of_line_area_or_volume` - Calculate the centroid of a line, area, or volume.
- `calculate_center_of_mass_with_variable_density` - Calculate center of mass when density varies.

#### 9-2 Composite Bodies (`composite_bodies`)

- `decompose_composite_body_into_standard_parts` - Decompose a composite area or volume into standard parts.
- `select_reference_axes_for_composite_centroid` - Select convenient reference axes.
- `use_signed_area_or_volume_for_holes` - Treat holes or removed regions as negative area or volume.
- `calculate_weighted_centroid_coordinates` - Calculate weighted centroid coordinates.
- `calculate_composite_center_of_mass` - Calculate center of mass for bodies with different densities or weights.
- `check_composite_centroid_location` - Check that the centroid lies in a physically reasonable location.

#### 9-3 Theorems of Pappus and Guldinus (`pappus_and_guldinus_theorems`)

- `identify_applicability_of_pappus_theorems` - Identify when a Pappus-Guldinus theorem applies.
- `calculate_surface_area_of_revolution` - Calculate a surface area of revolution from curve length and centroid path.
- `calculate_volume_of_revolution` - Calculate a volume of revolution from generating area and centroid path.
- `solve_for_unknown_centroid_using_pappus` - Solve for an unknown centroid location from a known surface area or volume.
- `check_axis_intersection_restriction` - Check the theorem's axis-intersection restriction.

### 10. Moments of Inertia for Areas (`area_moments_of_inertia`)

**Topic skills**

- Calculate area moments of inertia about specified axes.
- Use the parallel-axis theorem and radius of gyration.
- Determine moments of inertia of composite areas.

#### 10-1 Definition of Moments of Inertia for Areas (`definition_of_area_moment_of_inertia`)

- `distinguish_area_and_mass_moment_of_inertia` - Distinguish area moment of inertia from mass moment of inertia.
- `write_area_moment_integrals` - Write I_x = ∫y² dA and I_y = ∫x² dA.
- `calculate_area_moment_by_integration` - Calculate area moment of inertia by integration.
- `calculate_polar_area_moment_of_inertia` - Calculate polar area moment of inertia J_O = I_x + I_y.
- `use_standard_area_moment_formulas` - Use standard centroidal area-moment formulas.
- `report_area_moment_units` - Report area moment of inertia in length-to-the-fourth units.

#### 10-2 Parallel-Axis Theorem for an Area (`parallel_axis_theorem_for_area`)

- `identify_centroidal_axis_parallel_to_target_axis` - Identify the centroidal axis parallel to the target axis.
- `calculate_axis_offset_distance` - Calculate the perpendicular offset distance between parallel axes.
- `apply_parallel_axis_theorem_for_area` - Apply I = I_c + Ad².
- `avoid_invalid_parallel_axis_application` - Avoid applying the theorem to nonparallel or noncentroidal reference axes.

#### 10-3 Radius of Gyration of an Area (`radius_of_gyration_of_area`)

- `calculate_radius_of_gyration_from_area_moment` - Calculate radius of gyration using k = √(I/A).
- `calculate_area_moment_from_radius_of_gyration` - Calculate I from area and radius of gyration.
- `interpret_radius_of_gyration` - Interpret radius of gyration as an equivalent concentration distance.
- `select_correct_axis_for_radius_of_gyration` - Associate k_x, k_y, or k_O with the correct moment and axis.

#### 10-4 Moments of Inertia for Composite Areas (`moments_of_inertia_for_composite_areas`)

- `decompose_composite_area_for_inertia` - Decompose a composite area into standard component areas.
- `locate_component_centroids` - Locate each component centroid relative to the target axis.
- `apply_parallel_axis_to_each_component` - Apply the parallel-axis theorem to each component.
- `subtract_hole_area_moments` - Subtract the moment of inertia of holes and cutouts.
- `sum_component_area_moments` - Sum signed component moments of inertia.
- `check_composite_area_moment_magnitude_and_units` - Check magnitude, axis dependence, and length-to-the-fourth units.
