
%% Simulation of hot-dip galvanizing process
% For: Jose Daniel Hernandez Betancur
% Mater thesis title: "Detection of the critcal points of hot-dip galvanizing process:
% a focus on sustainability and sustainable development
% Master degree's name: Master in Engineering - Materials and Processes
% University: National University of Colombia - Medellin branch
% Date: 03 October, 2017
%%-----------------------------------------------------------------------------------------------------------

function [m_steel_T,m_rust_T,m_grease_and_oil_T,...
m_sln1_Ti,C_1i,m_saponified_T,m_remaining_grease_T,Q_1T,m_sln1,C_1,MW_grease_T,...
m_sln2_Ti,m_sln2_Tf,C_2f,N2,...
m_sln3_Ti,m_sln3_Tf,C_3i,C_3f,N3i,N3f,...
m_sln4_Ti,m_sln4_Tf,C_4i,C_4f,N4i,N4f,...
m_sln5_Ti,m_sln5_Tf,C_5f,N5,...
m_sln6_Ti,m_sln6_Tf,C_6i,C_6f,N6i,N6f,Q_6T,mNH4OH_added_T,mHCl_added_T,...
Q_7T,m_sln8_T,Q_8T,m_dross_T,m_ash_T,m_zn_coating_T,U_C_average,m_surface_area_T,...
eta_N_T,NN,N_times] = HDG(Items,Nsample)

% Items represents the amount of steel pieces which inputs to process
% each year

rand('state',sum(100*clock))

Tamb = norminv(rand(),22,2); % Initial environment temperature [oC]

%% Baths' initial conditions

% (1) Degreasing

[Vol_1,C_1,T_1] = initial_conditions(1);
rho_1 = density(T_1,C_1(1),1);

m_sln1 = rho_1* Vol_1; % Initial mass of NaOH solution [kg]
m_saponified_T = 0; % Saponified mass [kg]
m_remaining_grease_T = 0; % Remaining grease mass [kg]
Q_1T = m_sln1*(-627.6*(C_1(1) - 1.08)/16.73 + 4121.2)*...
(T_1 - Tamb); % Initial heat for degreasing [J]
Q1= 0; % Initial added heat for degreasing [J]

m_sln1_Ti = m_sln1;
C_1i = C_1;

% (2) Rinsing 1

Vol_2 = (2- 0.2*rand())*1*7;
m_sln2 = 1000*Vol_2;

% 1: NaOH
% 2: H2O
% 3: Grycerol
% 4: Sodium Carboxylates

C_2 = zeros(1,4);
C_2(2) = 100;
T_2 = Tamb;

m_sln2_Ti = m_sln2;
m_sln2_Tf = 0;
C_2f = zeros(1,4);
N2 = 0;

% (3) Normal Pickling

[Vol_3,C_3] = initial_conditions(2);
T_3 = Tamb;
rho_3 = density(T_3,C_3(1),2);
m_sln3 = rho_3* Vol_3; % Initial mass of HCl solution [kg]

m_sln3_Ti = m_sln3;
m_sln3_Tf = 0;
C_3f = zeros(1,3);
C_3i = C_3;
N3f = 0;
N3i = 1;

% (4) Abnormal Pickling

[Vol_4,C_4] = initial_conditions(3);
T_4 = Tamb;
rho_4 = density(T_4,C_4(1),2);
m_sln4 = rho_4* Vol_4; % Initial mass of HCl solution [kg]

m_sln4_Ti = m_sln4;
m_sln4_Tf = 0;
C_4f = zeros(1,4);
C_4i = C_4;
N4f = 0;
N4i = 1;

% (5) Rinsing 2

Vol_5 = (2- 0.2*rand())*1*7;
m_sln5 = 1000*Vol_5;

% 1: HCl
% 2: H2O
% 3: Fe2+
% 4: Zn2+

C_5 = zeros(1,4);
C_5(2) = 100;
T_5 = Tamb;

m_sln5_Ti = m_sln5;
m_sln5_Tf = 0;
C_5f = zeros(1,4);
N5 = 0;

% (6) Fluxing

[Vol_6,C_6,T_6,m_sln6,pH] = initial_conditions(4);
Q_6T = m_sln6*96.232*(T_6 - Tamb);
Q_6= 0;

mHCl_added_T = 0;
mNH4OH_added_T = 0;

m_sln6_Ti = m_sln6;
m_sln6_Tf = 0;
C_6f = zeros(1,9);
C_6i = C_6;
N6f = 0;
N6i = 1;

% (7) Drying
Q_7T = 0;
T_7 = 100;

% (8) Galvanizing
Vol_8 = (1.8 - 0.2*rand())*0.8*7;
m_sln8 = 6430*Vol_8;
m_sln8_T = m_sln8;
T_8 = norminv(rand(),450,1.6667);
Q_8T = m_sln8*1000*(0.3883*(419.5 - Tamb) + 100.9 + 0.4801*(T_8 - 419.5));
Q8 = 0;
m_dross_T = 0;
m_ash_T = 0;

m_steel_T = 0;
reprocessing = 0;

U_C_average = 0; % Quality's average utility
MW_grease_T = 0; % Molecular weight of greases to calculate and average
m_rust_T = 0; % Total mass of rust [kg]
m_grease_and_oil_T = 0; % Total mass of grease [kg]
m_zn_coating_T = 0; % Total mass of zinc coating [kg]
m_surface_area_T = 0; % Total surface mass of steel [kg]
eta_N_T = 0;
NN = 0;
Sum_items = 0;
N_times = 0;

while Sum_items <= Items % Number of items

N_times = N_times + 1;

% Environment temperature [oC]
Tamb = norminv(rand(),22,2);

number = rand();

%% Items

% Item's mass [kg]

if (0 <= number) && (number < 0.2909)
lot_size = round(unifinv(rand(),200,54000));
item_mass = unifrnd(0.02553,0.02555,lot_size,1);
elseif (0.2909 <= number) && (number < 0.3985)
lot_size = round(unifinv(rand(),576,29843));
item_mass = unifrnd(0.09651,0.09659,lot_size,1);
elseif (0.3985 <= number) && (number < 0.4935)
lot_size = round(unifinv(rand(),1092,23101));
item_mass = unifrnd(0.009428,0.009438,lot_size,1);
elseif (0.4935 <= number) && (number < 0.5876)
lot_size = round(unifinv(rand(),285,23661));
item_mass = unifrnd(0.08460,0.08466,lot_size,1);
elseif (0.5876 <= number) && (number < 0.6806)
lot_size = round(unifinv(rand(),46,37230));
item_mass = unifrnd(0.02440,0.02442,lot_size,1);
elseif (0.6806 <= number) && (number < 0.7549)
lot_size = round(unifinv(rand(),10000,24000));
item_mass = unifrnd(0.12283,0.12293,lot_size,1);
elseif (0.7549 <= number) && (number < 0.8220)
lot_size = round(unifinv(rand(),428,28636));
item_mass = unifrnd(0.07007,0.07013,lot_size,1);
elseif (0.8220 <= number) && (number < 0.8862)
lot_size = round(unifinv(rand(),4614,42930));
item_mass = unifrnd(0.05802,0.05808,lot_size,1);
elseif (0.8862 <= number) && (number < 0.9458)
lot_size = round(unifinv(rand(),3300,39600));
item_mass = unifrnd(0.08855,0.08863,lot_size,1);
elseif (0.9458 <= number) && (number <= 1)
lot_size = 111600;
item_mass = unifrnd(0.010611,0.010623,lot_size,1);
end

Sum_items = Sum_items + lot_size;
m_steel_T = m_steel_T + sum(item_mass);

X = sprintf('Pieza %d de la muestra %d.\n',Sum_items,Nsample);
disp(X)

coating_thickness = zeros(lot_size,1);
m_zn_coating = zeros(lot_size,1);

% Item's geometry

item_gauge = unifrnd(0.0003,0.0320,lot_size,1); % Item's gauge [m]
item_length = sqrt(item_mass./(7850.*item_gauge)); % Item's length [m]
item_surface_area = 2.*item_length.^2 + 4.*item_length.*item_gauge; % Item's susface area [m2]

% Item's chemical composition of structural steel [ % wt]

% (1) Iron, (2) Manganese, (3) Silicon, (4) Phosphorus and
% (5) Carbon

wt = zeros(lot_size,5);

wt(:,2) = unifrnd(0.5,1.7,lot_size,1); wt(:,3) = unifrnd(0.15,0.25,lot_size,1);
wt(:,4) = unifrnd(0,0.04,lot_size,1); wt(:,5) = unifrnd(0.15,0.3,lot_size,1);
wt(:,1) = 100*ones(lot_size,1) - sum(wt(:,2:5),2);

% Item's rust, oil and grases [kg]

P_degreasing = 0.3; % 30 % of items need to be degreased (assumption)
R_grease_steel = 10; % 12g of greases and oil x 1 ton of steel (assumption)

m_grease_and_oil = 0;
m_steel_greased = 0;
MW_grease = 41.0716/(1 - (0.02*rand() + 0.94));
MW_grease_T = MW_grease_T + MW_grease;

for i = 1:lot_size

if P_degreasing >= rand()

m_grease_and_oil = m_grease_and_oil + R_grease_steel*item_mass(i)*1e-6;
m_grease_and_oil_T = m_grease_and_oil_T + R_grease_steel*item_mass(i)*1e-6;
m_steel_greased = m_steel_greased + item_mass(i);

end

RE_index{i} = 'YES';
end
clear i

% between 300 and 590g rust x 1 m2 steel area (assumption)
R_rust_steelarea = unifrnd(300,590,lot_size,1);
m_rust = dot(R_rust_steelarea,item_surface_area)*1e-3;
m_rust_T = m_rust_T + m_rust;
m_surface_area_T = m_surface_area_T + m_rust*(55.845/70.8534)*(0.7/0.3);

%% Starting HDG process

% Step 1: Degreasing

[m_saponified,m_remaining_grease,Q1,m_sln1,C_1,T_1,m_sln1_remove] = ...
degreasing(m_grease_and_oil,MW_grease,m_sln1,C_1,T_1,m_steel_greased,Q1,Tamb);

m_saponified_T = m_saponified_T + m_saponified;
m_remaining_grease_T = m_remaining_grease_T + m_remaining_grease;
Q_1T = Q_1T + Q1;

% Step 2: Rinsing 1

if Sum_items >= (N2 + 1)*round(Items/54)

m_sln2_Tf = m_sln2_Tf + m_sln2;
C_2f = C_2f + C_2;
N2 = N2 + 1;

Vol_2 = (2- 0.2*rand())*1*7;
m_sln2 = 1000*Vol_2;
C_2 = zeros(1,4);
C_2(2) = 100;
T_2 = Tamb;

m_sln2_Ti = m_sln2_Ti + m_sln2;

end

aux_2 = m_sln2;
m_sln2 = m_sln2 + m_sln1_remove;
C_2 = [C_2(1)*aux_2 + C_1(1)*m_sln1_remove C_2(2)*aux_2 + C_1(2)*m_sln1_remove ...
C_2(3)*aux_2 + C_1(3)*m_sln1_remove C_2(4)*aux_2 + C_1(4)*m_sln1_remove]*(1/m_sln2);
T_2 = Tamb;

% Step 3: Pickling

P_reprocessing = 0.02; % 2 % of items need to be reprocessing (assumption)
random = zeros(lot_size,1);
steel_surface = sum(item_surface_area);
steel_mass = sum(item_mass);

while min(random) <= P_reprocessing

if reprocessing == 0

C_3_aux = 0.01*C_3(3)*m_sln3/Vol_3;

if C_3_aux >= 150

m_sln3_Tf = m_sln3_Tf + m_sln3;
C_3f = C_3f + C_3;
N3f = N3f + 1;

[Vol_3,C_3] = initial_conditions(2);
T_3 = Tamb;
rho_3 = density(T_3,C_3(1),2);
m_sln3 = rho_3* Vol_3;

m_sln3_Ti = m_sln3_Ti + m_sln3;
C_3i = C_3i + C_3;
N3i = N3i + 1;

end

[m_sln3,C_3,m_rust,m_sln3_remove,Vol_3] = ...
pickling(C_3,m_sln3,T_3,Vol_3,m_rust,steel_surface,steel_mass);

m_sln_remove_aux = m_sln3_remove;
C_aux = [C_3(1) C_3(2) C_3(3) 0];

elseif reprocessing == 1

C_4_aux_1 = 0.01*C_4(1)*m_sln4/Vol_4;

if C_4_aux_1 < 10

m_sln4_Tf = m_sln4_Tf + m_sln4;
C_4f = C_4f + C_4;
N4f = N4f + 1;

[Vol_4,C_4] = initial_conditions(3);
T_4 = Tamb;
rho_4 = density(T_4,C_4(1),2);
m_sln4 = rho_4* Vol_4;

m_sln4_Ti = m_sln4_Ti + m_sln4;
C_4i = C_4i + C_4;
N4i = N4i + 1;

end

[m_sln4,C_4,~,m_sln4_remove,Vol_4] = ...
pickling(C_4,m_sln4,T_4,Vol_4,m_coating_reprocessed,steel_surface,steel_mass);

m_sln_remove_aux = m_sln4_remove;
C_aux = C_4;
m_rust = 0;

end

% Step 4: Rinsing 2

if Sum_items >= (N5 + 1)*round(Items/54)

m_sln5_Tf = m_sln5_Tf + m_sln5;
C_5f = C_5f + C_5;
N5 = N5 + 1;

Vol_5 = (2- 0.2*rand())*1*7;
m_sln5 = 1000*Vol_5;
C_5 = zeros(1,4);
C_5(2) = 100;
T_5 = Tamb;

m_sln5_Ti = m_sln5_Ti + m_sln5;

end

aux_5 = m_sln5;
m_sln5 = m_sln5 + m_sln_remove_aux;
C_5 = [C_5(1)*aux_5 + C_aux(1)*m_sln_remove_aux C_5(2)*aux_5 + C_aux(2)*m_sln_remove_aux ...
C_5(3)*aux_5 + C_aux(3)*m_sln_remove_aux C_5(4)*aux_5 + C_aux(4)*m_sln_remove_aux]*(1/m_sln5);
T_5 = Tamb;

% Step 5: Fluxing

[Q_6,m_sln6,C_6,T_6,m_sln6_remove,mHCl_added,mNH4OH_added,pH] = ...
fluxing2(m_rust,m_sln6,C_6,T_6,steel_mass,Q_6,Tamb,Vol_6,pH);

Q_6T = Q_6T + Q_6;
mNH4OH_added_T = mNH4OH_added_T + mNH4OH_added;
mHCl_added_T = mHCl_added_T + mHCl_added;

C_6_aux = 0.01*C_6(8)*m_sln6/Vol_6;

if C_6_aux >= 5

m_sln6_Tf = m_sln6_Tf + m_sln6;
C_6f = C_6f + C_6;
N6f = N6f + 1;

[Vol_6,C_6,T_6,m_sln6] = initial_conditions(4);
Q_6 = 0;

m_sln6_Ti = m_sln6_Ti + m_sln6;
C_6i = C_6i + C_6;
N6i = N6i + 1;

end

% Step 6: Drying

HH = steel_mass*450 + 96.232*m_sln6_remove;
Q_7 = HH*(T_7 - T_6) + 22570600*0.01*C_6(4)*m_sln6_remove;
Q_7T = Q_7T + Q_7;

% Step 7: Galvanizing

m_dross = 0.01*norminv(rand(),0.75,0.0833)*steel_mass;
m_ash = 0.01*norminv(rand(),0.75,0.0833)*steel_mass;

m_dross_T = m_dross_T + m_dross;
m_ash_T = m_ash_T + m_ash;

if reprocessing == 0;

coating_thickness = (-3017 + 6.714*T_8)*rand(lot_size,1) + (4451 - 4.376*T_8)*wt(:,3) ...
+ (- 1.297e4 + 2.611*T_8)*wt(:,3).^2 + 1.145e4*wt(:,3).^3;
m_zn_coating = 7.*coating_thickness.*item_surface_area.*1e-3;
m_zn_coating_T = m_zn_coating_T + sum(m_zn_coating);

m_zn_lost = sum(m_zn_coating) + m_dross*0.01*norminv(rand(),95,0.3333) ...
+ m_ash*0.01*norminv(rand(),72.5,4.1667)*(65.409/81.41);

elseif reprocessing == 1

for i = 1:length(Position)

i_aux = Position(i);

coating_thickness(i_aux) = -3017 + 6.714*T_8 + (4451 - 4.376*T_8)*wt(i_aux,3) ...
+ (- 1.297e4 + 2.611*T_8)*wt(i_aux,3)^2 + 1.145e4*wt(i_aux,3)^3;
m_zn_coating(i_aux) = 7*coating_thickness(i_aux)*item_surface_area(i_aux)*1e-3;
m_zn_coating_T = m_zn_coating_T + m_zn_coating(i_aux);

m_zn_lost = m_zn_coating(i_aux) + m_dross*0.01*norminv(rand(),95,0.3333) ...
+ m_ash*0.01*norminv(rand(),72.5,4.1667)*(65.409/81.41);

end
clear i

reprocessing = 0;

end

T_8_o = T_8;
T_8 = norminv(rand(),450,1.6667);
lost = abs((T_8_o - Tamb)/435);

if T_8 > T_8_o

Ei = 1000*(0.3883*(419.5 - Tamb) + 100.9 + 0.4801*(T_8_o - 419.5));
Ef = 1000*(0.3883*(419.5 - Tamb) + 100.9 + 0.4801*(T_8 - 419.5));

Q8 = (m_sln8 - m_zn_lost)*Ef +(0.01*lost - 1)*m_sln8*Ei ...
+ 450*steel_mass*(T_8 - T_7);

else

Q8 = 0;

end

Q_8T = Q_8T + Q8;
m_sln8_T = m_sln8_T + m_zn_lost;

%% Ending HDG process

m_coating_reprocessed = 0;
steel_mass = 0;
steel_surface = 0;
N_reprocessing = 0;
clear Position

for j = 1:lot_size

if strcmp(RE_index{j},'YES') == 1

random(j) = rand();

if random(j) <= P_reprocessing

reprocessing = 1;
N_reprocessing = N_reprocessing + 1;
m_coating_reprocessed = m_coating_reprocessed + m_zn_coating(j);
steel_mass = steel_mass + item_mass(j);
steel_surface = steel_surface + item_surface_area(j);
Position(N_reprocessing) = j;

else

RE_index{j} = 'NO';

end

end

end
clear j

end

%% Quality: zinc coating thickness

for j = 1:lot_size

if (0 < item_gauge(j)*1e3) && (item_gauge(j)*1e3 < 1.5)
eta_N = 35;
elseif (1.5 <= item_gauge(j)*1e3) && (item_gauge(j)*1e3 < 3)
eta_N = 45;
elseif (3 <= item_gauge(j)*1e3) && (item_gauge(j)*1e3 < 6)
eta_N = 55;
elseif 6 <= item_gauge(j)*1e3
eta_N = 70;
end

U_C = min([1 coating_thickness(j)/eta_N]);
U_C_average = U_C_average + item_mass(j)*U_C;
eta_N_T = eta_N_T + eta_N;
NN = NN + 1;

end

end

if N3f == 0

m_sln3_Tf = m_sln3;
C_3f = C_3;
N3f = 1;

end

if N4f == 0

m_sln4_Tf = m_sln4;
C_4f = C_4;
N4f = 1;

end

if N6f == 0

m_sln6_Tf = m_sln6;
C_6f = C_6;
N6f = 1;

end

return
